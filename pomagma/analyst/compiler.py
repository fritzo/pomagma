import re

from pomagma.compiler.expressions import Expression, Expression_1
from pomagma.compiler.frontend import write_full_programs
from pomagma.compiler.parser import parse_string_to_expr, parse_theory_string
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.sugar import desugar_expr, desugar_sequent
from pomagma.compiler.util import memoize_arg, set_with

VAR = Expression_1("VAR")
RETURN = Expression_1("RETURN")
NRETURN = Expression_1("NRETURN")
NONEGATE = Expression_1("NONEGATE")


@memoize_arg
def guard_vars(expr):
    """Whereas pomagma.compiler follows the variable naming convention defined
    in pomagma.compiler.signature.is_var(), pomagma.analyst.validate and the
    puddle editor require VAR guarded variables."""
    if expr.name == "VAR":
        return expr
    if expr.is_var():
        return VAR(expr)
    args = list(map(guard_vars, expr.args))
    return Expression(expr.name, *args)


@memoize_arg
def unguard_vars(expr):
    if expr.name == "VAR":
        return expr.args[0]
    if expr.is_var():
        return expr
    args = list(map(unguard_vars, expr.args))
    return Expression(expr.name, *args)


def desugar(string):
    expr = parse_string_to_expr(string)
    expr = desugar_expr(expr)
    expr = guard_vars(expr)
    return str(expr)


def compile_solver(expr, theory):
    '''
    Produces a set of programs that finds values of term satisfying a theory.
    Inputs:
        expr - string, an expression with free variables
        theory - string representing a theory (in .theory format)
    Outputs:
        a program to be consumed by the virtual machine
    Example:
        expr = 's'
        theory = """
            # 6 constraints = 4 facts + 2 rules
            LESS APP V s s       NLESS x BOT      NLESS x I
            LESS APP s BOT BOT   --------------   ----------------
            EQUAL APP s I I      LESS I APP s x   LESS TOP APP s x
            LESS TOP APP s TOP
            """
    '''
    assert isinstance(expr, str), expr
    assert isinstance(theory, str), theory
    expr = desugar_expr(parse_string_to_expr(expr))
    assert expr.vars, expr
    theory = parse_theory_string(theory)
    facts = list(map(desugar_expr, theory["facts"]))
    rules = list(map(desugar_sequent, theory["rules"]))
    sequents = []
    can_infer_necessary = not rules and all(f.vars <= expr.vars for f in facts)
    can_infer_possible = expr.is_var()  # TODO generalize to injective exprs
    if can_infer_necessary:
        sequents.append(Sequent(facts, [NONEGATE(RETURN(expr))]))
    if can_infer_possible:
        fail = NONEGATE(NRETURN(expr))
        sequents += [Sequent([], [f, fail]) for f in facts]
        sequents += [
            Sequent(r.antecedents, set_with(r.succedents, fail)) for r in rules
        ]
    assert sequents, "Cannot infer anything"
    programs = []
    write_full_programs(programs, sequents, can_parallelize=False)
    program = "\n".join(programs)
    assert not re.search("FOR_BLOCK", program), "cannot parallelize"
    return program
