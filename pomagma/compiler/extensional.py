import itertools
from collections.abc import Callable

from pomagma.compiler.expressions import Expression, Expression_0, Expression_2
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.signature import is_positive
from pomagma.compiler.util import inputs, logger, methodof
from pomagma.util import TODO

I = Expression_0("I")
K = Expression_0("K")
F = Expression_0("F")
J = Expression_0("J")
R = Expression_0("R")
B = Expression_0("B")
CB = Expression_0("CB")
C = Expression_0("C")
W = Expression_0("W")
S = Expression_0("S")
A = Expression_0("A")
BOT = Expression_0("BOT")
TOP = Expression_0("TOP")
APP = Expression_2("APP")
COMP = Expression_2("COMP")
JOIN = Expression_2("JOIN")
RAND = Expression_2("RAND")


class AbstractionFailed(Exception):
    pass


def abstract_symmetric(
    self: "Expression",
    var: "Expression",
    atom: "Expression",
    operation: Callable[["Expression", "Expression"], "Expression"],
) -> "Expression":
    # K-compose-eta abstraction
    lhs, rhs = self.args
    if var in lhs.vars:
        if var in rhs.vars:
            return operation(lhs.abstract(var), rhs.abstract(var))
        if lhs == var:
            return APP(atom, rhs)
        return COMP(APP(atom, rhs), lhs.abstract(var))
    assert var in rhs.vars
    if rhs == var:
        return APP(atom, lhs)
    return COMP(APP(atom, lhs), rhs.abstract(var))


@methodof(Expression)
def abstract(self, var: "Expression") -> "Expression":
    assert isinstance(var, Expression)
    assert var.is_var()
    lhs: Expression
    rhs: Expression
    if self.name == "VAR":
        self = self.args[0]
    if self.is_var():
        if self == var:
            return I
        return APP(K, self)
    if self.is_fun():
        name = self.name
        if var not in self.vars:
            return APP(K, self)
        if name == "APP":
            # I,K,C,SW,COMP,eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                lhs_abs = lhs.abstract(var)
                if var in rhs.vars:
                    if rhs == var:
                        return APP(W, lhs_abs)
                    return APP(APP(S, lhs_abs), rhs.abstract(var))
                return APP(APP(C, lhs_abs), rhs)
            assert var in rhs.vars
            if rhs == var:
                return lhs
            return COMP(lhs, rhs.abstract(var))
        if name == "COMP":
            # K,B,CB,C,S,COMP,eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                lhs_abs = lhs.abstract(var)
                if var in rhs.vars:
                    return APP(APP(S, COMP(B, lhs_abs)), rhs.abstract(var))
                if lhs == var:
                    return APP(CB, rhs)
                return COMP(APP(CB, rhs), lhs_abs)
            assert var in rhs.vars
            if rhs == var:
                return APP(B, lhs)
            return COMP(APP(B, lhs), rhs.abstract(var))
        if name == "JOIN":
            return abstract_symmetric(self, var, J, JOIN)
        if name == "RAND":
            return abstract_symmetric(self, var, R, RAND)
        raise AbstractionFailed
    if self.is_rel():
        args = [arg.abstract(var) for arg in self.args]
        return Expression(self.name, *args)
    raise ValueError(f"bad expression: {self.name}")


class RequireVariable(Exception):
    pass


class SkipValidation(Exception):
    pass


def get_fresh(bound):
    for name in "abcdefghijklmnopqrstuvwxyz":
        fresh = Expression(name)
        if fresh not in bound:
            return fresh
    raise NotImplementedError("Exceeded fresh variable limit")


def pop_arg(args):
    if args:
        return args[0], args[1:]
    raise RequireVariable


def head_normalize(expr, *args):
    if expr.is_var():
        return [expr, *list(args)]
    assert expr.is_fun(), expr
    name = expr.name
    if name == "APP":
        lhs, rhs = expr.args
        return head_normalize(lhs, rhs, *args)
    if name == "COMP":
        lhs, rhs = expr.args
        arg0, args = pop_arg(args)
        return head_normalize(lhs, APP(rhs, arg0), *args)
    if name in ["BOT", "TOP"]:
        return [expr]
    if name == "I":
        arg0, args = pop_arg(args)
        return head_normalize(arg0, *args)
    if name == "K":
        arg0, args = pop_arg(args)
        arg1, args = pop_arg(args)
        return head_normalize(arg0, *args)
    if name == "F":
        arg0, args = pop_arg(args)
        arg1, args = pop_arg(args)
        return head_normalize(arg1, *args)
    if name == "B":
        arg0, args = pop_arg(args)
        arg1, args = pop_arg(args)
        arg2, args = pop_arg(args)
        return head_normalize(arg0, APP(arg1, arg2), *args)
    if name == "C":
        arg0, args = pop_arg(args)
        arg1, args = pop_arg(args)
        arg2, args = pop_arg(args)
        return head_normalize(arg0, arg2, arg1, *args)
    if name == "W":
        arg0, args = pop_arg(args)
        arg1, args = pop_arg(args)
        return head_normalize(arg0, arg1, arg1, *args)
    if name == "S":
        arg0, args = pop_arg(args)
        arg1, args = pop_arg(args)
        arg2, args = pop_arg(args)
        return head_normalize(arg0, arg2, APP(arg1, arg2), *args)
    if name == "CI":
        return head_normalize(C, I, *args)
    if name == "CB":
        return head_normalize(C, B, *args)
    if name in ["Y", "J", "JOIN", "R", "RAND", "U", "V", "P", "A"]:
        raise SkipValidation
    raise TODO(f"head normalize {name} expressions")


def validate(expr):
    assert expr.is_rel(), expr
    assert expr.name in ["LESS", "EQUAL"]
    if expr.name != "EQUAL":
        print(f"WARNING: not validating {expr}")
        return
    while True:
        try:
            lhs, rhs = expr.args
            lhs = head_normalize(lhs)
            rhs = head_normalize(rhs)
            assert len(lhs) == len(rhs), (
                f"Failed to validate\n  {expr}\nbecause\n  {lhs} != {rhs}"
            )
            assert lhs[0] == rhs[0], (
                f"Failed to validate\n  {expr}\nbecause  \n{lhs[0]} != {rhs[0]}"
            )
            for args in zip(lhs[1:], rhs[1:]):
                validate(Expression(expr.name, *args))
            break
        except RequireVariable:
            lhs, rhs = expr.args
            fresh = get_fresh(expr.vars)
            lhs = APP(lhs, fresh)
            rhs = APP(rhs, fresh)
            expr = Expression(expr.name, lhs, rhs)
        except SkipValidation:
            print(f"WARNING: not validating {expr}")
            return


@inputs(Expression)
def iter_eta_substitutions(expr):
    """
    Iterate over Hindley-style substitutions:
        [x/x], [x/a], [x/APP x a] (and maybe [x/COMP x a])
    """
    varlist = list(expr.vars)
    fresh = get_fresh(expr.vars)
    for cases in itertools.product(list(range(3)), repeat=len(varlist)):
        result = expr
        for var, case in zip(varlist, cases):
            if case == 0:
                pass  # do nothing
            elif case == 1:
                result = result.substitute(var, fresh)
            elif case == 2:
                result = result.substitute(var, APP(var, fresh))
            # elif case == 3:
            #    result = result.substitute(var, COMP(var, fresh))
        if any(cases):
            yield result.abstract(fresh)
        else:
            yield result


def iter_subsets(set_):
    list_ = list(set_)
    for cases in itertools.product([0, 1], repeat=len(list_)):
        yield {x for (x, case) in zip(list_, cases) if case}


@inputs(Expression)
def iter_closure_maps(expr):
    """Iterate over all closing abstractions, including variable
    coincidence."""
    if not expr.vars:
        yield expr
    else:
        for varset in iter_subsets(expr.vars):
            if varset:
                var = varset.pop()
                abstracted = expr
                for other in varset:
                    abstracted = abstracted.substitute(other, var)
                abstracted = abstracted.abstract(var)
                yield from iter_closure_maps(abstracted)


@inputs(Expression)
def iter_closure_permutations(expr):
    """Iterate over all closing permutations."""
    if not expr.vars:
        yield expr
    else:
        for var in expr.vars:
            abstracted = expr.abstract(var)
            yield from iter_closure_maps(abstracted)


@inputs(Expression)
def iter_closures(expr):
    if expr.name in ["OPTIONALLY", "NONEGATE"]:
        expr = expr.args[0]
    try:
        assert expr.is_rel(), expr
        lhs, rhs = expr.args
        if not expr.vars:
            yield expr
        elif is_positive(expr.name):
            for expr2 in iter_eta_substitutions(expr):
                assert expr2.is_rel(), expr2
                for expr3 in iter_closure_maps(expr2):
                    assert expr3.is_rel(), expr3
                    yield expr3
        else:
            for expr2 in iter_closure_permutations(expr):
                yield expr2
    except AbstractionFailed:
        pass


@inputs(Sequent)
def derive_facts(rule):
    facts = set()
    if len(rule.antecedents) == 0 and len(rule.succedents) == 1:
        expr = next(iter(rule.succedents))
        for derived in iter_closures(expr):
            lhs, rhs = derived.args
            if lhs != rhs:
                assert derived.is_rel()
                facts.add(derived)
        facts = sorted(facts, key=lambda expr: len(expr.polish))
        logger(f"derived {len(facts)} facts from {expr}")
    return facts
