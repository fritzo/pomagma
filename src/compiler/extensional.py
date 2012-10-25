from pomagma.compiler.util import TODO, inputs, methodof
from pomagma.compiler.signature import is_positive
from pomagma.compiler.expressions import Expression
from pomagma.compiler.sequents import Sequent

I = Expression('I')
K = Expression('K')
J = Expression('J')
B = Expression('B')
C = Expression('C')
W = Expression('W')
S = Expression('S')
APP = lambda x, y: Expression('APP', [x, y])
COMP = lambda x, y: Expression('COMP', [x, y])
JOIN = lambda x, y: Expression('JOIN', [x, y])


@methodof(Expression)
def abstract(self, var):
    assert isinstance(var, Expression)
    assert var.is_var()
    if var not in self.vars:
        return APP(K, self)
    elif self.is_var():
        return I
    elif self.is_fun():
        name = self.name
        if name == 'APP':
            # IKCSW-compose-eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                lhs_abs = lhs.abstract(var)
                if var in rhs.vars:
                    if lhs == rhs:
                        return APP(W, lhs_abs)
                    else:
                        return APP(APP(S, lhs_abs), rhs.abstract(var))
                else:
                    return APP(APP(C, lhs_abs), rhs)
            else:
                assert var in rhs.vars
                if rhs == var:
                    return lhs
                else:
                    return COMP(lhs, rhs.abstract(var))
        elif name == 'COMP':
            # KBCS-compose-eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                lhs_abs = lhs.abstract(var)
                if var in rhs.vars:
                    return APP(APP(S, COMP(B, lhs_abs)), rhs.abstract(var))
                else:
                    return COMP(APP(APP(C, B), rhs), lhs_abs)
            else:
                assert var in rhs.vars
                if rhs == var:
                    return APP(B, lhs)
                else:
                    return COMP(APP(B, lhs_abs), rhs.abstract(var))
        elif name == 'JOIN':
            # K-compose-eta abstraction
            if var in lhs.vars:
                if var in rhs.vars:
                    return JOIN(lhs.abstract(var), rhs.abstract(var))
                elif lhs == var:
                    return APP(J, rhs)
                else:
                    return COMP(APP(J, rhs), lhs.abstract(var))
            else:
                assert var in rhs.vars
                if rhs == var:
                    return APP(J, lhs)
                else:
                    return COMP(APP(J, lhs), rhs.abstract(var))
        else:
            raise ValueError('bad expression name: %s' % name)
    else:
        raise ValueError('bad expression: %s' % name)


@inputs(Expression)
def iter_eta_substitutions(expr):
    TODO('')


@inputs(Expression)
def iter_closure_maps(expr):
    TODO('')


@inputs(Expression)
def iter_closure_permutations(expr):
    TODO('')


@inputs(Expression)
def iter_closures(expr):
    assert expr.is_rel()
    lhs, rhs = expr.args
    if not expr.vars:
        yield expr
    elif is_positive(expr.name):
        for expr2 in iter_eta_substitutions(expr):
            for expr3 in iter_closure_maps(expr2):
                yield expr3
    else:
        for expr2 in iter_closure_permutations(expr):
            yield expr2
    raise StopIteration


@inputs(Sequent)
def iter_derived(rule):
    if rule.antecedents or len(rule.succedents) != 1:
        raise StopIteration
    else:
        expr = iter(rule.succedents).next()
        return iter_closures(expr)
