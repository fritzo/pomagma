from pomagma.compiler import extensional
from pomagma.compiler.expressions import Expression, Expression_0, Expression_2
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.util import inputs

assert extensional  # pacify pyflakes


A = Expression_0("A")
Y = Expression_0("Y")
CI = Expression_0("CI")
APP = Expression_2("APP")
COMP = Expression_2("COMP")
EQUAL = Expression_2("EQUAL")


@inputs(Expression)
def desugar_expr(self):
    expr = Expression(self.name, *list(map(desugar_expr, self.args)))
    if expr.name == "FUN":
        var, body = expr.args
        assert var.is_var(), var
        expr = body.abstract(var)
    elif expr.name == "FIX":
        var, body = expr.args
        assert var.is_var(), var
        expr = APP(Y, body.abstract(var))
    elif expr.name == "PAIR":
        x, y = expr.args
        expr = COMP(APP(CI, y), APP(CI, x))
    elif expr.name == "ABIND":
        r, s, body = expr.args
        assert r.is_var(), r
        assert s.is_var(), s
        expr = APP(A, body.abstract(s).abstract(r))
    elif expr.name == "FIXES":
        typ, inhab = expr.args
        expr = EQUAL(APP(typ, inhab), inhab)
    return expr


@inputs(Sequent)
def desugar_sequent(self):
    return Sequent(
        {desugar_expr(a) for a in self.antecedents},
        {desugar_expr(s) for s in self.succedents},
    )


@inputs(dict)
def desugar_theory(theory):
    rules = list(map(desugar_sequent, theory["rules"]))
    facts = []
    for fact in map(desugar_expr, theory["facts"]):
        if fact.vars:
            rules.append(Sequent(set(), {fact}))
        else:
            facts.append(fact)
    return {"facts": facts, "rules": rules}
