from pomagma.compiler import extensional
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_0
from pomagma.compiler.expressions import Expression_2
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.util import inputs

assert extensional  # pacify pyflakes


A = Expression_0('A')
Y = Expression_0('Y')
APP = Expression_2('APP')
EQUAL = Expression_2('EQUAL')


@inputs(Expression)
def desugar_expr(self):
    expr = Expression.make(self.name, *map(desugar_expr, self.args))
    if expr.name == 'FUN':
        var, body = expr.args
        assert var.is_var(), var
        expr = body.abstract(var)
    elif expr.name == 'FIX':
        var, body = expr.args
        assert var.is_var(), var
        expr = APP(Y, body.abstract(var))
    elif expr.name == 'ABIND':
        s, r, body = expr.args
        assert s.is_var(), s
        assert r.is_var(), r
        expr = APP(A, body.abstract(r).abstract(s))
    elif expr.name == 'FIXES':
        typ, inhab = expr.args
        expr = EQUAL(APP(typ, inhab), inhab)
    return expr


@inputs(Sequent)
def desugar_sequent(self):
    return Sequent(
        set(desugar_expr(a) for a in self.antecedents),
        set(desugar_expr(s) for s in self.succedents))


@inputs(dict)
def desugar_theory(theory):
    rules = map(desugar_sequent, theory['rules'])
    facts = []
    for fact in map(desugar_expr, theory['facts']):
        if fact.vars:
            rules.append(Sequent(set(), set([fact])))
        else:
            facts.append(fact)
    return {'facts': facts, 'rules': rules}
