import sys
import math
import inspect
import pomagma.util
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_2
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.sequents import assert_normal
from pomagma.compiler.sequents import normalize
from pomagma.compiler.util import inputs
from pomagma.compiler.util import log_sum_exp
from pomagma.compiler.util import logger
from pomagma.compiler.util import set_with
from pomagma.compiler.util import set_without
from pomagma.compiler.util import sortedset
from pomagma.compiler.util import union


def assert_in(element, set_):
    assert element in set_, '{0} not in {1}'.format(element, set_)


def assert_not_in(element, set_):
    assert element not in set_, '{0} in {1}'.format(element, set_)


def assert_subset(subset, set_):
    assert subset <= set_, '{0} not <= {1}'.format(subset, set_)


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


# ----------------------------------------------------------------------------
# Strategies


OBJECT_COUNT = 1e4                          # optimize for this many obs
LOGIC_COST = OBJECT_COUNT / 256.0           # AVX operations are cheap
LOG_OBJECT_COUNT = math.log(OBJECT_COUNT)


def add_costs(costs):
    return (log_sum_exp(*[LOG_OBJECT_COUNT * c for c in costs]) /
            LOG_OBJECT_COUNT)


class Strategy(object):

    def cost(self):
        return math.log(self.op_count()) / LOG_OBJECT_COUNT

    def __lt__(self, other):
        s = repr(self)
        o = repr(other)
        return (len(s), s) < (len(o), o)


class Iter(Strategy):

    def __init__(self, var, body):
        assert var.is_var(), 'Iter var is not a Variable: {0}'.format(var)
        assert isinstance(body, Strategy), 'Iter body is not a Strategy'
        self._repr = None
        self.var = var
        self.body = body
        self.tests = []
        self.lets = {}

    def add_test(self, test):
        assert isinstance(test, Test), 'add_test arg is not a Test'
        self.tests.append(test.expr)

    def add_let(self, let):
        assert isinstance(let, Let), 'add_let arg is not a Let'
        assert let.var not in self.lets, 'add_let var is not in Iter.lets'
        self.lets[let.var] = let.expr

    def __repr__(self):
        if self._repr is None:
            tests = ['if {0}'.format(t) for t in self.tests]
            lets = ['let {0}'.format(l) for l in sorted(self.lets.iterkeys())]
            self._repr = 'for {0}: {1}'.format(
                ' '.join([str(self.var)] + tests + lets),
                self.body)
        return self._repr

    def validate(self, bound):
        assert_not_in(self.var, bound)
        bound = set_with(bound, self.var)
        for test in self.tests:
            assert_subset(test.vars, bound)
        for var, expr in self.lets.iteritems():
            assert_subset(expr.vars, bound)
            assert_not_in(var, bound)
            bound.add(var)
        self.body.validate(bound)

    def op_count(self):
        test_count = len(self.tests) + len(self.lets)
        logic_cost = LOGIC_COST * test_count
        object_count = OBJECT_COUNT * 0.5 ** test_count
        let_cost = len(self.lets)
        return logic_cost + object_count * (let_cost + self.body.op_count())

    def optimize(self):
        parent = self
        child = self.body
        new_lets = set()
        while isinstance(child, Test) or isinstance(child, Let):
            if isinstance(child, Let):
                new_lets.add(child.var)
            optimizable = (
                self.var in child.expr.vars and
                child.expr.vars.isdisjoint(new_lets) and
                sum(1 for arg in child.expr.args if self.var == arg) == 1 and
                sum(1 for arg in child.expr.args if self.var in arg.vars) == 1
            )
            if optimizable:
                if isinstance(child, Test):
                    self.add_test(child)
                else:
                    self.add_let(child)
                child = child.body
                parent.body = child
            else:
                parent = child
                child = child.body
        child.optimize()


# TODO injective function inverse need not be iterated
class IterInvInjective(Strategy):

    def __init__(self, fun, body):
        assert fun.arity == 'InjectiveFunction'
        self.fun = fun.name
        self.value = fun.var
        (self.var,) = fun.args
        self.body = body

    def __repr__(self):
        return 'for {0} {1}: {2}'.format(self.fun, self.var, self.body)

    def validate(self, bound):
        assert_in(self.value, bound)
        assert_not_in(self.var, bound)
        self.body.validate(set_with(bound, self.var))

    def op_count(self):
        return 4.0 + 0.5 * self.body.op_count()  # amortized

    def optimize(self):
        self.body.optimize()


class IterInvBinary(Strategy):

    def __init__(self, fun, body):
        assert fun.arity in ['BinaryFunction', 'SymmetricFunction']
        self.fun = fun.name
        self.value = fun.var
        self.var1, self.var2 = fun.args
        self.body = body

    def __repr__(self):
        return 'for {0} {1} {2}: {3}'.format(
            self.fun, self.var1, self.var2, self.body)

    def validate(self, bound):
        assert_in(self.value, bound)
        assert_not_in(self.var1, bound)
        assert_not_in(self.var2, bound)
        self.body.validate(set_with(bound, self.var1, self.var2))

    def op_count(self):
        return 4.0 + 0.25 * OBJECT_COUNT * self.body.op_count()  # amortized

    def optimize(self):
        self.body.optimize()


class IterInvBinaryRange(Strategy):

    def __init__(self, fun, fixed, body):
        assert fun.arity in ['BinaryFunction', 'SymmetricFunction']
        self.fun = fun.name
        self.value = fun.var
        self.var1, self.var2 = fun.args
        assert self.var1 != self.var2
        assert self.var1 == fixed or self.var2 == fixed
        self.lhs_fixed = (fixed == self.var1)
        self.body = body

    def __repr__(self):
        if self.lhs_fixed:
            return 'for {0} ({1}) {2}: {3}'.format(
                self.fun, self.var1, self.var2, self.body)
        else:
            return 'for {0} {1} ({2}): {3}'.format(
                self.fun, self.var1, self.var2, self.body)

    def validate(self, bound):
        assert self.value in bound
        if self.lhs_fixed:
            assert_in(self.var1, bound)
            assert_not_in(self.var2, bound)
            self.body.validate(set_with(bound, self.var2))
        else:
            assert_in(self.var2, bound)
            assert_not_in(self.var1, bound)
            self.body.validate(set_with(bound, self.var1))

    def op_count(self):
        return 4.0 + 0.5 * self.body.op_count()  # amortized

    def optimize(self):
        self.body.optimize()


class Let(Strategy):

    def __init__(self, expr, body):
        assert isinstance(body, Strategy)
        assert expr.is_fun()
        self.var = expr.var
        self.expr = expr
        self.body = body

    def __repr__(self):
        return 'let {0}: {1}'.format(self.var, self.body)

    def validate(self, bound):
        assert_subset(self.expr.vars, bound)
        assert_not_in(self.var, bound)
        self.body.validate(set_with(bound, self.var))

    def op_count(self):
        return 1.0 + 0.5 * self.body.op_count()

    def optimize(self):
        self.body.optimize()


class Test(Strategy):

    def __init__(self, expr, body):
        assert not expr.is_var()
        assert isinstance(body, Strategy)
        self.expr = expr
        self.body = body

    def __repr__(self):
        return 'if {0}: {1}'.format(self.expr, self.body)

    def validate(self, bound):
        assert_subset(self.expr.vars, bound)
        self.body.validate(bound)

    def op_count(self):
        return 1.0 + self.body.op_count()

    def optimize(self):
        self.body.optimize()


class Ensure(Strategy):

    def __init__(self, expr):
        assert expr.args, 'expr is not compound: {0}'.format(expr)
        self.expr = expr

    def __repr__(self):
        return 'ensure {0}'.format(self.expr)

    def validate(self, bound):
        assert_subset(self.expr.vars, bound)

    def op_count(self):
        fun_count = 0
        if self.expr.name == 'EQUATION':
            for arg in self.expr.args:
                if arg.is_fun():
                    fun_count += 1
        return [1.0, 1.0 + 0.5 * 1.0, 2.0 + 0.75 * 1.0][fun_count]

    def optimize(self):
        pass


# ----------------------------------------------------------------------------
# Sequents


@inputs(Sequent)
def compile_full(seq):
    results = []
    if seq.optional:
        logger('skipped optional rule {0}'.format(seq))
        return results
    for derived_seq in normalize(seq):
        context = set()
        bound = set()
        ranked = rank_compiled(derived_seq, context, bound)
        results.append(min(ranked))
    assert results, 'failed to compile {0}'.format(seq)
    logger('derived {0} rules from {1}'.format(len(results), seq))
    return results


@inputs(Sequent)
def get_events(seq):
    events = set()
    if seq.optional:
        logger('skipped optional rule {0}'.format(seq))
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
    context = set([atom])
    bound = get_bound(atom)
    results = []
    for normal in normalize_given(seq, atom, bound):
        # print 'DEBUG normal =', normal
        ranked = rank_compiled(normal, context, bound)
        logger('optimizing {0} versions'.format(len(ranked)))
        results.append(min(ranked))
    assert results, 'failed to compile {0} given {1}'.format(seq, atom)
    logger('derived {0} rules from {1} | {2}'.format(len(results), atom, seq))
    return results


@inputs(Sequent)
def rank_compiled(seq, context, bound):
    assert_normal(seq)
    antecedents = sortedset(seq.antecedents - context)
    (succedent,) = list(seq.succedents)
    ranked = []
    POMAGMA_DEBUG('{} | {} |- {}', list(bound), list(antecedents), succedent)
    for strategy in iter_compiled(antecedents, succedent, bound):
        strategy.validate(bound)
        # print 'DEBUG', '-' * 8
        # print 'DEBUG', strategy
        strategy.optimize()
        # print 'DEBUG', strategy
        strategy.validate(bound)
        ranked.append((strategy.cost(), seq, strategy))
        print_dot()
    assert ranked, 'failed to compile {0}'.format(seq)
    return ranked


def iter_compiled(antecedents, succedent, bound):
    '''
    Iterate through the space of strategies, narrowing heuristically.
    '''
    assert isinstance(antecedents, sortedset)
    assert isinstance(succedent.consts, sortedset)

    yielded = False

    # ensure
    if not antecedents and succedent.vars <= bound:
        POMAGMA_DEBUG('ensure {}', succedent)
        yield Ensure(succedent)
        yielded = True
        return

    # bind succedent constants
    for c in succedent.consts:
        if c.var not in bound:
            bound_c = set_with(bound, c.var)
            POMAGMA_DEBUG('bind succedent constant {}', c)
            for s in iter_compiled(antecedents, succedent, bound_c):
                yield Let(c, s)
                yielded = True
            return  # HEURISTIC bind eagerly in arbitrary order

    # bind antecedent constants
    for a in antecedents:
        if not a.args and a.var not in bound:
            assert a.is_fun(), a
            antecedents_a = sortedset(set_without(antecedents, a))
            bound_a = set_with(bound, a.var)
            POMAGMA_DEBUG('bind antecedent constant {}', a)
            for s in iter_compiled(antecedents_a, succedent, bound_a):
                yield Let(a, s)
                yielded = True
            return  # HEURISTIC bind eagerly in arbitrary order

    # conditionals
    for a in antecedents:
        if a.is_rel():
            if a.vars <= bound:
                antecedents_a = sortedset(set_without(antecedents, a))
                POMAGMA_DEBUG('conditional {}', a)
                for s in iter_compiled(antecedents_a, succedent, bound):
                    yield Test(a, s)
                    yielded = True
        else:
            assert a.is_fun(), a
            if a.vars <= bound and a.var in bound:
                antecedents_a = sortedset(set_without(antecedents, a))
                POMAGMA_DEBUG('conditional {}', a)
                for s in iter_compiled(antecedents_a, succedent, bound):
                    yield Test(a, s)
                    yielded = True
        if yielded:
            return  # HEURISTIC test eagerly in arbitrary order

    # find & bind variable
    for a in antecedents:
        if a.is_fun():
            if a.vars <= bound:
                assert a.var not in bound
                antecedents_a = sortedset(set_without(antecedents, a))
                bound_a = set_with(bound, a.var)
                POMAGMA_DEBUG('bind variable {}', a)
                for s in iter_compiled(antecedents_a, succedent, bound_a):
                    yield Let(a, s)
                    yielded = True
            else:
                # TODO find inverse if injective function
                pass
        if yielded:
            return  # HEURISTIC bind eagerly in arbitrary order

    # iterate forward
    forward_vars = set()
    for a in antecedents:
        a_free = a.vars - bound
        if len(a_free) == 1:
            forward_vars |= a_free
    for v in forward_vars:
        bound_v = set_with(bound, v)
        POMAGMA_DEBUG('iterate forward {}', v)
        for s in iter_compiled(antecedents, succedent, bound_v):
            yield Iter(v, s)
            yielded = True

    # iterate backward
    for a in antecedents:
        if a.is_fun() and a.var in bound:
            a_free = a.vars - bound
            assert len(a_free) in [0, 1, 2]
            nargs = len(a.args)
            assert nargs in [0, 1, 2]
            if nargs and a_free:
                bound_v = bound | a_free
                antecedents_a = sortedset(set_without(antecedents, a))
                POMAGMA_DEBUG('iterate backward {}', a)
                if nargs == 1 and len(a_free) == 1:
                    # TODO injective function inverse need not be iterated
                    for s in iter_compiled(antecedents_a, succedent, bound_v):
                        yield IterInvInjective(a, s)
                        yielded = True
                elif nargs == 2 and len(a_free) == 1 and len(a.vars) == 2:
                    for s in iter_compiled(antecedents_a, succedent, bound_v):
                        (fixed,) = list(a.vars - a_free)
                        yield IterInvBinaryRange(a, fixed, s)
                        yielded = True
                elif nargs == 2 and len(a_free) == 2:
                    for s in iter_compiled(antecedents_a, succedent, bound_v):
                        yield IterInvBinary(a, s)
                        yielded = True

    if yielded:
        return  # HEURISTIC iterate locally eagerly

    # iterate anything
    free = union(a.vars for a in antecedents) | succedent.vars - bound
    for v in free:
        bound_v = set_with(bound, v)
        POMAGMA_DEBUG('iterate non-locally')
        for s in iter_compiled(antecedents, succedent, bound_v):
            yield Iter(v, s)
            yielded = True

    assert yielded
