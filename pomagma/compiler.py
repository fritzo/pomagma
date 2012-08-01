import re
import math
import itertools
from pomagma.util import TODO, union, set_with, set_without, log_sum_exp

#-----------------------------------------------------------------------------
# Syntax

class Expression:
    def __init__(self, _repr):
        self._repr = _repr
        self._hash = hash(_repr)

    def __repr__(self):
        return self._repr

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._repr == other._repr


class Variable(Expression):
    def __init__(self, name):
        if isinstance(name, str):
            assert not re.match('[A-Z]', name[-1])
        else:
            name = re.sub('[(), ]+', '_', repr(name))
        self.name = name
        Expression.__init__(self, name)

    def get_vars(self):
        return set([self])

    def get_constants(self):
        return set()

    def get_tests(self):
        return set()


class Compound(Expression):
    def __init__(self, name, *children):
        assert re.match('[A-Z]', name[-1])
        self.name = name
        self.children = list(children)
        Expression.__init__(self, ' '.join([name] + map(repr, children)))

    def get_vars(self):
        return union([child.get_vars() for child in self.children])

    def get_constants(self):
        if self.children:
            return union([c.get_constants() for c in self.children])
        else:
            assert isinstance(self, Function)
            return set([self])

    def get_atom(self):
        return self.__class__(self.name, *map(Variable, self.children))

    def get_tests(self):
        result = set([self.get_atom()])
        for c in self.children:
            result |= c.get_tests()
        return result


class Function(Compound):
    pass


class Relation(Compound):
    pass


EQUAL = lambda x, y: Relation('EQUAL', x, y)
LESS = lambda x, y: Relation('LESS', x, y)
NLESS = lambda x, y: Relation('NLESS', x, y)


#-----------------------------------------------------------------------------
# Strategies

OBJECT_COUNT = 1e4
LOGIC_COST = OBJECT_COUNT / 256.0
LOG_OBJECT_COUNT = math.log(OBJECT_COUNT)


def add_costs(*args):
    return log_sum_exp(*[LOG_OBJECT_COUNT * a for a in args]) / LOG_OBJECT_COUNT


class Strategy(object):
    def cost(self):
        return math.log(self._cost()) / math.log(OBJECT_COUNT)


class Iter(Strategy):
    def __init__(self, var, body):
        assert isinstance(var, Variable)
        assert isinstance(body, Strategy)
        self.var = var
        self.body = body
        self.tests = []
        self.lets = {}

    def copy(self):
        result = Iter(self.var, self.body)
        result.tests = self.tests[:]
        result.lets = self.lets.copy()
        return result

    def add_test(self, test):
        assert isinstance(test, Test)
        self.tests.append(test)

    def add_let(self, let):
        assert isinstance(let, Let)
        assert let.var not in self.lets
        self.lets[let.var] = let.expr

    def __repr__(self):
        tests = ['if {}'.format(t) for t in self.tests]
        lets = ['let {}'.format(l) for l in self.lets.keys()]
        return 'for {}: {}'.format(
                ' '.join([str(self.var)] + tests + lets),
                self.body)

    def _cost(self):
        test_count = len(self.tests) + len(self.lets)
        logic_cost = LOGIC_COST * test_count
        object_count = OBJECT_COUNT * 0.5 ** test_count
        let_cost = len(self.lets)
        return logic_cost + object_count * (let_cost + self.body._cost())

    def optimize(self):
        parent = self
        child = self.body
        while isinstance(child, Test) or isinstance(child, Let):
            if self.var in child.expr.get_vars():
                if isinstance(child, Test):
                    self.add_test(child)
                else:
                    self.add_let(child)
                child = child.body
                parent.body = child
            else:
                parent = child
                child = child.body


class Let(Strategy):
    def __init__(self, expr, body):
        assert isinstance(expr, Function)
        assert isinstance(body, Strategy)
        self.var = Variable(expr)
        self.expr = expr
        self.body = body

    def __repr__(self):
        return 'let {}: {}'.format(self.var, self.body)

    def _cost(self):
        return 1.0 + 0.5 * self.body._cost()

    def optimize(self):
        self.body.optimize()


class Test(Strategy):
    def __init__(self, expr, body):
        assert isinstance(expr, Expression)
        assert isinstance(body, Strategy)
        self.expr = expr
        self.body = body

    def __repr__(self):
        return 'if {}: {}'.format(self.expr, self.body)

    def _cost(self):
        return 1.0 + self.body._cost()

    def optimize(self):
        self.body.optimize()


class Ensure(Strategy):
    def __init__(self, expr):
        assert isinstance(expr, Compound)
        self.expr = expr

    def __repr__(self):
        return 'ensure {}'.format(self.expr)

    def _cost(self):
        return 1.0

    def optimize(self):
        pass


class OBSOLETE_Strategy(object):
    def __init__(self, sequence, succedent):
        self.sequence = list(sequence)  # TODO generalize to trees
        self.succedent = Ensure(succedent)
        self._str = ' '.join(map(str, self.sequence))
        self._repr = ' '.join(map(str, self.sequence + [self.succedent]))
        self._hash = hash(self._repr)

    def __eq__(self, other):
        return self._repr == other._repr

    def __hash__(self):
        return self._hash

    def __str__(self):
        return self._str

    def __repr__(self):
        return self._repr

    def cost(self):
        cost = 1.0
        for op in reversed(self.sequence):
            cost = op.cost(cost)
        return math.log(cost) / math.log(OBJECT_COUNT)

    def optimize(self):
        '''
        Pull tests into preceding iterators
        '''
        last_iter = None
        sequence = []
        for op in self.sequence:
            if isinstance(op, Iter):
                last_iter = op.copy()
                sequence.append(last_iter)
            elif isinstance(op, Test):
                if last_iter and last_iter.var in op.expr.get_vars():
                    last_iter.add_test(op)
                else:
                    sequence.append(op)
            else:
                assert isinstance(op, Let)
                if last_iter and last_iter.var in op.expr.get_vars():
                    last_iter.add_let(op)
                else:
                    self.last_iter = None
                    sequence.append(op)
        return Strategy(sequence, self.succedent.expr)


#-----------------------------------------------------------------------------
# Sequents


class Sequent(object):
    def __init__(self, antecedents, succedents):
        antecedents = set(antecedents)
        succedents = set(succedents)
        for expr in antecedents | succedents:
            assert isinstance(expr, Compound)
        self.antecedents = antecedents
        self.succedents = succedents

    def __str__(self):
        return '{} |- {}'.format(
            ', '.join(map(str, self.antecedents)),
            ', '.join(map(str, self.succedents)))

    def get_vars(self):
        return union([e.get_vars() for e in self.antecedents | self.succedents])

    def get_constants(self):
        return union([e.get_constants()
                      for e in self.antecedents | self.succedents])

    def _is_normal(self):
        '''
        A sequent is normalized if it has a single consequent of the form
            Relation Variable Variable
        and each antecedent is of one of the minimal forms
            Function Variable Variable  (which abbreviates Var = Fun Var Var)
            Relation Variable Variable
        '''
        if len(self.succedents) != 1:
            return False
        for node in self.antecedents | self.succedents:
            for child in node.children:
                if isinstance(child, Compound):
                    return False
        return True

    def _normalized(self):
        '''
        Return a list of normalized sequents.
        '''
        if not self.succedents:
            TODO('allow multiple succedents')
        elif len(self.succedents) > 1:
            TODO('allow empty succedents')
        succedent = self.succedents.copy().pop()
        succedents = set([succedent.get_atom()])
        antecedents = union([r.get_tests() for r in self.antecedents] +
                            [e.get_tests() for e in succedent.children])
        return [Sequent(antecedents, succedents)]

    def get_events(self):
        return union([s.antecedents for s in self._normalized()])

    # TODO deal with EQUAL succedent where one side need not exist
    def compile(self):
        free = self.get_vars()
        constants = self.get_constants()

        def rank(s):
            # HEURISTIC test for constants first
            for c in constants:
                s = Let(c, s)
            s.optimize()
            return s.cost(), s

        context = set(constants)
        bound = set(map(Variable, constants))

        results = []
        for part in self._normalized():
            ranked = []
            for v in free:
                rank_v = lambda s: rank(Iter(v, s))
                bound_v = set_with(bound, v)
                ranked += map(rank_v, part._compile(context, bound_v))
            print '# optimizing over {} versions'.format(len(ranked))
            results.append(min(ranked))
        return results

    def compile_given(self, atom):
        assert isinstance(atom, Compound)
        context = set([atom])
        bound = atom.get_vars()
        if isinstance(atom, Function):
            bound.add(Variable(atom))
        constants = self.get_constants()

        def rank(s):
            # HEURISTIC test for constants first
            for c in constants:
                s = Let(c, s)
            s.optimize()
            return s.cost(), s

        context |= set(constants)
        bound |= set(map(Variable, constants))

        results = []
        for part in self._normalized():
            if atom in part.antecedents:
                ranked = map(rank, part._compile(context, bound))
                print '# optimizing over {} versions'.format(len(ranked))
                results.append(min(ranked))
        return results

    def _compile(self, context, bound):
        assert self._is_normal()
        antecedents = self.antecedents - context
        succedent = self.succedents.copy().pop()
        return iter_compiled(antecedents, succedent, bound)


def iter_compiled(antecedents, succedent, bound):
    #print 'DEBUG', list(antecedents), succedent, list(bound)
    assert bound

    if not antecedents:
        return [Ensure(succedent)]

    results = []

    # conditionals
    for a in antecedents:
        if isinstance(a, Relation):
            if a.get_vars() <= bound:
                antecedents_a = set_without(antecedents, a)
                for s in iter_compiled(antecedents_a, succedent, bound):
                    results.append(Test(a, s))
        else:
            assert isinstance(a, Function)
            if a.get_vars() <= bound and Variable(a) in bound:
                antecedents_a = set_without(antecedents, a)
                for s in iter_compiled(antecedents_a, succedent, bound):
                    results.append(Test(a, s))
        if results:
            return results  # HEURISTIC ignore test order
    #if results:
    #    return results  # HEURISTIC test eagerly

    # find & bind variable
    for a in antecedents:
        if isinstance(a, Function):
            if a.get_vars() <= bound:
                var_a = Variable(a)
                assert var_a not in bound
                antecedents_a = set_without(antecedents, a)
                bound_a = set_with(bound, var_a)
                for s in iter_compiled(antecedents_a, succedent, bound_a):
                    results.append(Let(a, s))
        if results:
            return results  # HEURISTIC ignore bind order
    #if results:
    #    return results  # HEURISTIC bind eagerly

    # iterate forward eagerly
    for a in antecedents:
        # works for both Relation and Function antecedents
        if a.get_vars() & bound:
            for v in a.get_vars() - bound:
                bound_v = set_with(bound, v)
                for s in iter_compiled(antecedents, succedent, bound_v):
                    results.append(Iter(v, s))
    if results:
        return results  # HEURISTIC iterate forward eagerly

    # iterate backward
    for a in antecedents:
        if isinstance(a, Function):
            if Variable(a) in bound:
                for v in a.get_vars() - bound:
                    bound_v = set_with(bound, v)
                    for s in iter_compiled(antecedents, succedent, bound_v):
                        results.append(Iter(v, s))

    return results

class Theory(object):
    def __init__(self, sequents):
        self.sequents = sequents

    def compile(self):
        TODO()
