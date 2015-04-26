import sys
import inspect
import pomagma.util
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_1
from pomagma.compiler.expressions import Expression_2
from pomagma.compiler.plans import Ensure
from pomagma.compiler.plans import Iter
from pomagma.compiler.plans import IterInvBinary
from pomagma.compiler.plans import IterInvBinaryRange
from pomagma.compiler.plans import IterInvInjective
from pomagma.compiler.plans import Let
from pomagma.compiler.plans import Test
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.sequents import assert_normal
from pomagma.compiler.sequents import normalize
from pomagma.compiler.util import inputs
from pomagma.compiler.util import logger
from pomagma.compiler.util import memoize_args
from pomagma.compiler.util import set_with
from pomagma.compiler.util import set_without
from pomagma.compiler.util import sortedset
from pomagma.compiler.util import union


MIN_STACK_DEPTH = float('inf')


def stack_depth():
    global MIN_STACK_DEPTH
    depth = len(inspect.stack())
    MIN_STACK_DEPTH = min(MIN_STACK_DEPTH, depth)
    return depth - MIN_STACK_DEPTH


class DotPrinter(object):
    def __init__(self, out=sys.stdout):
        self.out = out
        self.count = 0

    def __call__(self, every=1000):
        assert every > 0
        self.count = (self.count + 1) % every
        if self.count == 0:
            self.out.write('.')
            self.out.flush()


print_dot = DotPrinter()


def POMAGMA_DEBUG_0(*args):
    pass


def POMAGMA_DEBUG_1(message, *args):
    print 'DEBUG{}'.format(' ' * stack_depth()),
    print message.format(*args)


if pomagma.util.LOG_LEVEL >= pomagma.util.LOG_LEVEL_DEBUG:
    POMAGMA_DEBUG = POMAGMA_DEBUG_1
else:
    POMAGMA_DEBUG = POMAGMA_DEBUG_0


EQUAL = Expression_2('EQUAL')
UNKNOWN = Expression_1('UNKNOWN')


@inputs(Sequent)
def compile_full(seq):
    results = []
    if seq.optional:
        logger('skipped optional rule {}', seq)
        return results
    for derived_seq in normalize(seq):
        context = frozenset()
        bound = frozenset()
        results.append(optimize_given(derived_seq, context, bound))
    assert results, 'failed to compile {0}'.format(seq)
    logger('derived {} rules from {}', len(results), seq)
    return results


@inputs(Sequent)
def get_events(seq):
    events = set()
    if seq.optional:
        logger('skipped optional rule {}', seq)
        return events
    free_vars = seq.vars
    for sequent in normalize(seq):
        for antecedent in sequent.antecedents:
            if antecedent.name == 'EQUAL':
                lhs, rhs = antecedent.args
                assert lhs.is_var() and rhs.is_var(), antecedent
                # HACK ignore equation antecedents
            else:
                events.add(antecedent)
        # HACK to deal with Equation args
        succedent = iter(sequent.succedents).next()
        for arg in succedent.args:
            if not arg.is_var():
                events.add(arg)
        antecedent_vars = union(a.vars for a in sequent.antecedents)
        for var in succedent.vars & free_vars - antecedent_vars:
            compound_count = sum(1 for arg in succedent.args if arg.args)
            in_count = sum(1 for arg in succedent.args if var in arg.vars)
            # if the var is in a compound in both succedent.args,
            # then succedent.args are sufficient events.
            if in_count < 2 or compound_count < 2:
                events.add(var)
    return events


def get_bound(atom):
    if atom.is_fun():
        return set_with(atom.vars, atom.var)
    else:
        return atom.vars


@inputs(Sequent, Expression)
def normalize_given(seq, atom, bound=None):
    if bound is None:
        bound = get_bound(atom)
    for normal in normalize(seq):
        if atom in normal.antecedents or atom.is_var():
            yield normal
        # HACK to deal with Equation args
        succedent = iter(normal.succedents).next()
        if succedent.name == 'EQUAL':
            lhs, rhs = succedent.args
            if lhs == atom:
                yield Sequent(
                    set_with(normal.antecedents, lhs),
                    set([EQUAL(lhs.var, rhs)]))
            elif rhs == atom:
                yield Sequent(
                    set_with(normal.antecedents, rhs),
                    set([EQUAL(lhs, rhs.var)]))


@inputs(Sequent, Expression)
def compile_given(seq, atom):
    context = frozenset([atom])
    bound = frozenset(get_bound(atom))
    normals = sorted(normalize_given(seq, atom, bound))
    assert normals, 'failed to compile {0} given {1}'.format(seq, atom)
    logger('derived {} rules from {} | {}', len(normals), atom, seq)
    return [optimize_given(n, context, bound) for n in normals]


@inputs(Sequent, frozenset, frozenset)
def optimize_given(seq, context, bound):
    assert_normal(seq)
    antecedents = sortedset(seq.antecedents - context)
    (succedent,) = list(seq.succedents)
    POMAGMA_DEBUG('{} | {} |- {}', list(bound), list(antecedents), succedent)
    plan = optimize_plan(antecedents, succedent, bound)
    plan.validate(bound)
    return plan.cost, seq, plan


@memoize_args
def optimize_plan(antecedents, succedent, bound):
    '''
    Iterate through the space of plans, narrowing heuristically.
    '''
    assert isinstance(antecedents, sortedset)
    assert isinstance(succedent.consts, sortedset)

    # ensure
    if not antecedents and succedent.vars <= bound:
        POMAGMA_DEBUG('ensure {}', succedent)
        return Ensure.make(succedent)

    # conditionals
    # HEURISTIC test eagerly in arbitrary order
    for a in antecedents:
        if a.is_rel():
            if a.vars <= bound:
                antecedents_a = sortedset(set_without(antecedents, a))
                POMAGMA_DEBUG('test relation {}', a)
                body = optimize_plan(antecedents_a, succedent, bound)
                return Test.make(a, body)
        else:
            assert a.is_fun(), a
            if a.vars <= bound and a.var in bound:
                antecedents_a = sortedset(set_without(antecedents, a))
                POMAGMA_DEBUG('test function {}', a)
                body = optimize_plan(antecedents_a, succedent, bound)
                return Test.make(a, body)

    # find & bind variable
    # HEURISTIC bind eagerly in arbitrary order
    for a in antecedents:
        if a.is_fun():
            if a.vars <= bound:
                assert a.var not in bound
                antecedents_a = sortedset(set_without(antecedents, a))
                bound_a = set_with(bound, a.var)
                POMAGMA_DEBUG('let {}', a)
                body = optimize_plan(antecedents_a, succedent, bound_a)
                return Let.make(a, body)
            else:
                # TODO find inverse if injective function
                pass

    results = []

    # iterate unknown
    if succedent.is_rel() and succedent.name != 'EQUAL':  # TODO handle EQUAL
        s_free = succedent.vars - bound
        if len(succedent.vars) == len(succedent.args) and len(s_free) == 1:
            v = iter(s_free).next()
            bound_v = set_with(bound, v)
            POMAGMA_DEBUG('iterate unknown {}', v)
            body = optimize_plan(antecedents, succedent, bound_v)
            results.append(Iter.make(v, Test.make(UNKNOWN(succedent), body)))

    # iterate forward
    forward_vars = set()
    for a in antecedents:
        a_free = a.vars - bound
        if len(a_free) == 1:
            forward_vars |= a_free
    for v in forward_vars:
        bound_v = set_with(bound, v)
        POMAGMA_DEBUG('iterate forward {}', v)
        body = optimize_plan(antecedents, succedent, bound_v)
        results.append(Iter.make(v, body))

    # iterate backward
    for a in antecedents:
        if a.is_fun() and a.args and a.var in bound and not (a.vars <= bound):
            nargs = len(a.args)
            a_free = a.vars - bound
            bound_v = bound | a_free
            antecedents_a = sortedset(set_without(antecedents, a))
            assert len(a_free) in [0, 1, 2]
            assert nargs in [0, 1, 2]
            POMAGMA_DEBUG('iterate backward {}', a)
            if nargs == 1 and len(a_free) == 1:
                # TODO injective function inverse need not be iterated
                body = optimize_plan(antecedents_a, succedent, bound_v)
                results.append(IterInvInjective.make(a, body))
            elif nargs == 2 and len(a_free) == 1 and len(a.vars) == 2:
                (fixed,) = list(a.vars - a_free)
                body = optimize_plan(antecedents_a, succedent, bound_v)
                results.append(IterInvBinaryRange.make(a, fixed, body))
            elif nargs == 2 and len(a_free) == 2:
                body = optimize_plan(antecedents_a, succedent, bound_v)
                results.append(IterInvBinary.make(a, body))

    # HEURISTIC iterate locally eagerly
    if results:
        return min(results)

    # iterate anything
    for v in union(a.vars for a in antecedents) | succedent.vars - bound:
        bound_v = set_with(bound, v)
        POMAGMA_DEBUG('iterate non-locally')
        body = optimize_plan(antecedents, succedent, bound_v)
        results.append(Iter.make(v, body))

    return min(results)
