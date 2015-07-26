from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_1
from pomagma.compiler.frontend import write_full_programs
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.parser import parse_theory_string
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.sequents import get_inverses
from pomagma.compiler.sugar import desugar_expr
from pomagma.compiler.sugar import desugar_sequent
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import set_with

VAR = Expression_1('VAR')
RETURN = Expression_1('RETURN')
NRETURN = Expression_1('NRETURN')
NONEGATE = Expression_1('NONEGATE')


@memoize_arg
def guard_vars(expr):
    '''
    Whereas pomagma.compiler follows the variable naming convention defined in
    pomagma.compiler.signature.is_var(), pomagma.analyst.validate
    and the puddle editor require VAR guarded variables.
    '''
    if expr.name == 'VAR':
        return expr
    elif expr.is_var():
        return VAR(expr)
    else:
        args = map(guard_vars, expr.args)
        return Expression.make(expr.name, *args)


def desugar(string):
    expr = parse_string_to_expr(string)
    expr = desugar_expr(expr)
    expr = guard_vars(expr)
    return str(expr)


def is_invertible(succedent):
    # TODO find better way to detect invertability
    return succedent.arity in ['Variable', 'InjectiveFunction']


def compile_solver(result, constraints):
    '''
    Produces programs that solve the problem {RETURN result | constraints}.
    Inputs:
        result - a string representing an expression with free variables
        constraints - a list of strings representing statements to be
          satisfied by the free variables.
    Outputs:
        a program to be consumed by the virtual machine
    Example:
        result = 'APP CI x'
        constraints = ['FIXES SEMI x', 'NLESS x TOP']
        produces a program that should return ['APP CI TOP', 'APP CI I']
    '''
    antecedents = map(parse_string_to_expr, constraints)
    result = parse_string_to_expr(result)
    assert result.is_term(), result
    succedent = RETURN(result)
    sequent = Sequent(antecedents, [succedent])
    sequent = desugar_sequent(sequent)
    sequents = [sequent]
    if is_invertible(result):
        sequents += sorted(get_inverses(sequent))
    sequents = [
        Sequent(s.antecedents, map(NONEGATE, s.succedents))
        for s in sequents
    ]
    programs = []
    write_full_programs(programs, sequents)
    program = '\n'.join(programs)
    return program


def compile_cosolver(var, theory):
    '''
    Produces programs that solve the problem {not NRETURN var | theory}.
    Inputs:
        var - string, the name of the free variable
        theory - string representing a theory (in .theory format)
    Outputs:
        a program to be consumed by the virtual machine
    Example:
        var = 's'
        constraints = """
            # 6 constraints = 4 facts + 2 rules
            LESS APP V s s       NLESS x BOT      NLESS x I
            LESS APP s BOT BOT   --------------   ----------------
            EQUAL APP s I I      LESS I APP s x   LESS TOP APP s x
            LESS TOP APP s TOP
            """
    '''
    assert isinstance(var, basestring), var
    assert isinstance(theory, basestring), theory
    var = Expression.make(var)
    assert var.is_var, var
    theory = parse_theory_string(theory)
    facts = map(desugar_expr, theory['facts'])
    rules = map(desugar_sequent, theory['rules'])
    fail = NONEGATE(NRETURN(var))
    sequents = [Sequent([], [f, fail]) for f in facts]
    sequents += [
        Sequent(r.antecedents, set_with(r.succedents, fail))
        for r in rules
    ]
    programs = []
    write_full_programs(programs, sequents)
    program = '\n'.join(programs)
    return program
