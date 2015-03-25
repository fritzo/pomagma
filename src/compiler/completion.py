from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import NotNegatable
from pomagma.compiler.expressions import try_get_negated
from pomagma.compiler.util import function
from pomagma.compiler.util import inputs
from pomagma.compiler.util import union


BOT = Expression('BOT')
TOP = Expression('TOP')


# TODO compile this from *.rules, rather than hand-coding
@inputs(set)
def complete_step(facts):
    result = set()
    equal = set(p for p in facts if p.name == 'EQUAL')
    less = set(p for p in facts if p.name == 'LESS')
    nless = set(p for p in facts if p.name == 'NLESS')
    # |- NLESS TOP BOT
    result.add(Expression('NLESS', TOP, BOT))
    # |- LESS x x
    # |- LESS x TOP
    # |- LESS BOT x
    for term in union(p.terms for p in facts):
        result.add(Expression('LESS', term, term))
        result.add(Expression('LESS', BOT, term))
        result.add(Expression('LESS', term, TOP))
    # EQUAL x y |- LESS x y
    # EQUAL x y |- LESS y x
    for p in equal:
        lhs, rhs = p.args
        result.add(Expression('LESS', lhs, rhs))
        result.add(Expression('LESS', rhs, lhs))
    # LESS x y, LESS y x |- EQUAL x y
    for p in less:
        lhs, rhs = p.args
        if Expression('LESS', rhs, lhs) in less:
            result.add(Expression('EQUAL', lhs, rhs))
    # LESS x y, LESS y z |- LESS x z
    for p in less:
        x, y = p.args
        for q in less:
            if q.args[0] == y:
                y, z = q.args
                result.add(Expression('LESS', x, z))
    # LESS x y, NLESS x z |- NLESS y z
    for p in less:
        x, y = p.args
        for q in nless:
            if q.args[0] == x:
                x, z = q.args
                result.add(Expression('NLESS', y, z))
    # NLESS x z, LESS y z |- NLESS x y
    for p in nless:
        x, z = p.args
        for q in less:
            if q.args[1] == z:
                y, z = q.args
                result.add(Expression('NLESS', x, y))
    return result


@inputs(set, function)
def close_under(facts, closure_op):
    boundary = set(facts)
    closed = set()
    while boundary:
        closed |= boundary
        boundary = closure_op(closed) - closed
    return closed


@inputs(set)
def complete(facts):
    return close_under(facts, complete_step)


@inputs(set)
def all_consistent(facts):
    completed = complete(facts)
    negated = set()
    for p in completed:
        try:
            negated.update(try_get_negated(p))
        except NotNegatable:
            pass
    return negated.isdisjoint(completed)


class Inconsistent(Exception):
    pass


@inputs(set)
def try_simplify(facts):
    if not all_consistent(facts):
        raise Inconsistent
    # TODO try to eliminate redundant antecedents
    return facts
