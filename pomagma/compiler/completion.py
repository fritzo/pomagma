import contextlib

from pomagma.compiler.expressions import (
    Expression,
    Expression_0,
    Expression_2,
    NotNegatable,
    try_get_negated,
)
from pomagma.compiler.util import (
    function,
    inputs,
    set_with,
    set_without,
    sortedset,
    union,
)

BOT = Expression_0("BOT")
TOP = Expression_0("TOP")
I = Expression_0("I")
K = Expression_0("K")
F = Expression_0("F")
J = Expression_0("J")
EQUAL = Expression_2("EQUAL")
LESS = Expression_2("LESS")
NLESS = Expression_2("NLESS")

# this will be completed below
basic_facts = {
    NLESS(TOP, BOT),
    NLESS(I, BOT),
    NLESS(TOP, I),
    NLESS(K, BOT),
    NLESS(TOP, K),
    NLESS(K, F),
    NLESS(F, BOT),
    NLESS(TOP, F),
    NLESS(F, K),
    NLESS(J, BOT),
    NLESS(TOP, J),
    LESS(K, J),
    NLESS(J, K),
    LESS(F, J),
    NLESS(J, F),
    NLESS(I, K),
    NLESS(K, I),
    NLESS(I, F),
    NLESS(F, I),
    NLESS(I, J),
    NLESS(J, I),
}


# TODO compile this from *.rules, rather than hand-coding
@inputs(set)
def complete_step(terms, relevant_facts):
    def step(facts):
        result = relevant_facts | facts
        equal = [p for p in result if p.name == "EQUAL"]
        less = [p for p in result if p.name == "LESS"]
        nless = [p for p in result if p.name == "NLESS"]
        # |- EQUAL x x
        # |- LESS x x
        # |- LESS x TOP
        # |- LESS BOT x
        for x in terms:
            result.add(EQUAL(x, x))
            result.add(LESS(x, x))
            result.add(LESS(BOT, x))
            result.add(LESS(x, TOP))
        # EQUAL x y |- LESS x y
        # EQUAL x y |- LESS y x
        for p in equal:
            x, y = p.args
            result.add(LESS(x, y))
            result.add(LESS(y, x))
        # LESS x y, LESS y x |- EQUAL x y
        for p in less:
            x, y = p.args
            q = LESS(y, x)
            if q in result:
                result.add(EQUAL(x, y))
        # LESS x y, LESS y z |- LESS x z
        for p in less:
            x, y = p.args
            for q in less:
                if q.args[0] == y:
                    y, z = q.args
                    result.add(LESS(x, z))
        # LESS x y, NLESS x z |- NLESS y z
        for p in less:
            x, y = p.args
            for q in nless:
                if q.args[0] == x:
                    x, z = q.args
                    result.add(NLESS(y, z))
        # NLESS x z, LESS y z |- NLESS x y
        for p in nless:
            x, z = p.args
            for q in less:
                if q.args[1] == z:
                    y, z = q.args
                    result.add(NLESS(x, y))
        return result

    return step


@inputs((set, frozenset, sortedset), function)
def close_under(facts, closure_op):
    closed = set()
    boundary = facts
    while boundary:
        closed |= boundary
        boundary = closure_op(closed)
        boundary -= closed
    return closed


def complete(facts, terms=set()):
    terms = terms | union(p.terms for p in facts) | {BOT, TOP}
    relevant_facts = {p for p in basic_facts if p.terms <= terms}
    return close_under(facts, complete_step(terms, relevant_facts))


basic_facts = complete(basic_facts)


@inputs(set)
def all_consistent(completed):
    negated = set()
    for p in completed:
        with contextlib.suppress(NotNegatable):
            negated.update(try_get_negated(p))
    return negated.isdisjoint(completed)


class Inconsistent(Exception):
    pass


def weaken_facts(facts, fact):
    assert fact in facts
    if fact.is_rel():
        without = set_without(facts, fact)
        yield without
        if fact.name == "EQUAL":
            lhs, rhs = fact.args
            yield set_with(without, LESS(lhs, rhs))
            yield set_with(without, LESS(rhs, lhs))


def simplify_step(completed):
    terms = union(p.terms for p in completed)

    def step(fact_sets):
        result = fact_sets.copy()
        for facts in fact_sets:
            for fact in facts:
                for simple in weaken_facts(facts, fact):
                    frozen = frozenset(simple)
                    if frozen not in result:
                        if complete(simple, terms) == completed:
                            result.add(frozen)
        return result

    return step


def objective_function(facts):
    weight = sum(2 if p.name == "EQUAL" else 1 for p in facts if p.is_rel())
    string = ", ".join(sorted(str(p) for p in facts))
    return weight, len(string), string


@inputs(set)
def try_simplify_antecedents(facts):
    completed = complete(facts)
    if not all_consistent(completed):
        raise Inconsistent
    simple = {frozenset(facts)}
    simple = close_under(simple, simplify_step(completed))
    return set(min(simple, key=objective_function))


def strengthen_sequent(fact):
    while fact.arity == "UnaryMeta":
        fact = fact.args[0]
    assert fact.is_rel(), fact
    if fact.name == "LESS":
        lhs, rhs = fact.args
        if lhs == TOP or rhs == BOT:
            return EQUAL(lhs, rhs)
    return fact


def weaken_sequent(fact):
    if fact.arity == "UnaryMeta":
        return Expression(fact.name, weaken_sequent(fact.args[0]))
    assert fact.is_rel(), fact
    if fact.name == "EQUAL":
        lhs, rhs = fact.args
        if lhs == TOP or rhs == BOT:
            return LESS(lhs, rhs)
        if rhs == TOP or lhs == BOT:
            return LESS(rhs, lhs)
    return fact
