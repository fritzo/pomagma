import re
import sys
import math
from textwrap import dedent
from pomagma.util import TODO, union, set_with, set_without, log_sum_exp


def logger(message):
    print '#', message


def indent(text):
    return '    ' + text.replace('\n', '\n    ')


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

    def get_signature(self):
        return set()


class Variable(Expression):
    def __init__(self, name):
        if isinstance(name, str):
            assert not re.match('[A-Z_]', name[-1]),\
                    'Bad variable name: {0}'.format(name)
        else:
            name = re.sub('[(), ]+', '_', repr(name))
        self.name = name
        Expression.__init__(self, name)

    def get_vars(self):
        return set([self])

    def get_constants(self):
        return set()

    def as_antecedent(self):
        return set()


class Compound(Expression):
    def __init__(self, name, *children):
        assert re.match('[A-Z_]', name[-1]),\
                    'Bad coumpound name: {0}'.format(name)
        self.name = name
        self.children = list(children)
        Expression.__init__(self, ' '.join([name] + map(repr, children)))

    def get_vars(self):
        return union([child.get_vars() for child in self.children])

    def get_constants(self):
        if self.children:
            return union([c.get_constants() for c in self.children])
        else:
            assert isinstance(self, Function),\
                    'Relation {} has no children'.format(self.name)
            return set([self])

    def as_atom(self):
        return self.__class__(self.name, *map(Variable, self.children))

    def as_antecedent(self):
        antecedents = union([c.as_antecedent() for c in self.children])
        antecedents.add(self.as_atom())
        return antecedents

    def is_antecedent(self):
        return all(isinstance(c, Variable) for c in self.children)

    def as_succedent(self, bound=set()):
        antecedents = union([c.as_antecedent() for c in self.children])
        succedent = self.as_atom()
        return antecedents, succedent

    def is_succedent(self):
        return all(isinstance(c, Variable) for c in self.children)

    def get_signature(self):
        return union(c.get_signature() for c in self.children)


class Function(Compound):
    #def get_vars(self):
    #    if self.children:
    #        return Compound.get_vars(self)
    #    else:
    #        return set([Variable(self)])
    def get_signature(self):
        return set([self.name]) | union(c.get_signature()
                                        for c in self.children)

# TODO SymmetricFunction
# TODO InjectiveFunction

class Relation(Compound):
    def is_positive(self):
        return self.name[0] != 'N'

    def negated(self):
        'Returns a disjunction'
        name = re.sub('^(NN)+', '', 'N{0}'.format(self.name))
        return set([Relation(name, *self.children)])


class Equation(Compound):
    def __init__(self, lhs, rhs):
        Compound.__init__(self, 'EQUAL', lhs, rhs)

    def is_positive(self):
        return True

    def negated(self):
        'Returns a disjunction'
        lhs, rhs = self.children
        return set([Relation('NLESS', lhs, rhs), Relation('NLESS', rhs, lhs)])

    def as_atom(self):
        return Equation(*map(Variable, self.children))

    def as_succedent(self, bound=set()):
        lhs, rhs = self.children
        antecedents = set()
        if isinstance(lhs, Function):
            var = Variable(lhs)
            if var in bound:
                antecedents |= lhs.as_antecedent()
                lhs = var
            else:
                antecedents |= union([c.as_antecedent() for c in lhs.children])
                lhs = lhs.as_atom()
        if isinstance(rhs, Function):
            var = Variable(rhs)
            if var in bound:
                antecedents |= rhs.as_antecedent()
                rhs = var
            else:
                antecedents |= union([c.as_antecedent() for c in rhs.children])
                rhs = rhs.as_atom()
        succedent = Equation(lhs, rhs)
        return antecedents, succedent

    def is_succedent(self):
        return all(isinstance(c, Variable) or c.is_succedent()
                   for c in self.children)


EQUAL = lambda x, y: Equation(x, y)
LESS = lambda x, y: Relation('LESS', x, y)
NLESS = lambda x, y: Relation('NLESS', x, y)

UNARY_FUNCTIONS = ['QUOTE']
BINARY_FUNCTIONS = ['APP', 'COMP']
SYMMETRIC_FUNCTIONS = ['JOIN', 'RAND']

SYMBOL_TABLE = {
    'EQUAL': (2, EQUAL),
    'LESS': (2, LESS),
    'NLESS': (2, NLESS),
    }

def _declare_unary(name):
    SYMBOL_TABLE[name] = (1, lambda x: Function(name, x))
for name in UNARY_FUNCTIONS:
    _declare_unary(name)

def _declare_binary(name):
    SYMBOL_TABLE[name] = (2, lambda x, y: Function(name, x, y))
for name in BINARY_FUNCTIONS + SYMMETRIC_FUNCTIONS:
    _declare_binary(name)


TYPE_TABLE = dict(
    [('LESS', 'PositiveOrder'), ('NLESS', 'NegativeOrder')] +
    [(name, 'UnaryFunction') for name in UNARY_FUNCTIONS] +
    [(name, 'BinaryFunction') for name in BINARY_FUNCTIONS] +
    [(name, 'SymmetricFunction') for name in SYMMETRIC_FUNCTIONS] +
    [])


#-----------------------------------------------------------------------------
# Strategies


OBJECT_COUNT = 1e4
LOGIC_COST = OBJECT_COUNT / 256.0
LOG_OBJECT_COUNT = math.log(OBJECT_COUNT)


def add_costs(*args):
    return (log_sum_exp(*[LOG_OBJECT_COUNT * a for a in args])
            / LOG_OBJECT_COUNT)


class Strategy(object):
    def cost(self):
        return math.log(self.op_count()) / LOG_OBJECT_COUNT


class Iter(Strategy):
    def __init__(self, var, body):
        assert isinstance(var, Variable), 'Iter var is not a Variable'
        assert isinstance(body, Strategy), 'Iter body is not a Strategy'
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
        tests = ['if {0}'.format(t) for t in self.tests]
        lets = ['let {0}'.format(l) for l in self.lets.keys()]
        return 'for {0}: {1}'.format(
                ' '.join([str(self.var)] + tests + lets),
                self.body)

    def cpp_lines(self):
        body = ['oid_t {0} = *iter;'.format(self.var)]
        for var, expr in self.lets.iteritems():
            body.append('oid_t {0} = {1}({2});'.format(
                var, expr.name, ', '.join(map(str, expr.children))))
        body += self.body.cpp_lines()
        body = map(indent, body)
        sets = []
        for test in self.tests:
            sets.append('TODO {0}'.format(str(test)))
        for var, expr in self.lets.iteritems():
            sets.append('TODO {0}'.format(str(var)))
        lines = []
        if len(sets) == 0:
            lines += [
                'const dense_set & set = carrier.support();',
                ]
        elif len(sets) == 1:
            one_set = iter(sets).next()
            lines += [
                'dense_set set(carrier.item_dim(), {0});'.format(one_set),
                ]
        else:
            lines += [
                'dense_set set(carrier.item_dim());',
                'set.set_union({0})'.format(', '.join(sets)),
                ]
        lines += [
            'for (dense_set::iterator iter(set); iter.ok(); iter.next()) {',
            ] + body + [
            '}',
            ]
        return lines

    def op_count(self):
        test_count = len(self.tests) + len(self.lets)
        logic_cost = LOGIC_COST * test_count
        object_count = OBJECT_COUNT * 0.5 ** test_count
        let_cost = len(self.lets)
        return logic_cost + object_count * (let_cost + self.body.op_count())

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
        child.optimize()


class IterInvUnary(Strategy):
    def __init__(self, fun, body):
        self.fun = fun.name
        self.value = str(Variable(fun))
        (self.var,) = fun.children
        self.body = body

    def __repr__(self):
        return 'for {0} {1}: {2}'.format(self.fun, self.var, self.body)

    def cpp_lines(self):
        body = []
        body.append('oid_t {0} = iter.arg();'.format(self.var))
        body += self.body.cpp_lines()
        body = ['    ' + line for line in body]
        iter = 'unary_function::inverse_iterator iter({0})'.format(self.value)
        return [
            'for ({0}; iter.ok(); iter.next()) {{'.format(iter),
            ] + body + [
            '}',
            ]

    def op_count(self):
        return 4.0 + 0.5 * self.body.op_count()  # amortized

    def optimize(self):
        self.body.optimize()


class IterInvBinary(Strategy):
    def __init__(self, fun, body):
        self.fun = fun.name
        self.value = str(Variable(fun))
        self.var1, self.var2 = fun.children
        self.body = body

    def __repr__(self):
        return 'for {0} {1} {2}: {3}'.format(
                self.fun, self.var1, self.var2, self.body)

    def cpp_lines(self):
        body = []
        body.append('oid_t {0} = iter.lhs();'.format(self.var1))
        body.append('oid_t {0} = iter.rhs();'.format(self.var2))
        body += self.body.cpp_lines()
        body = ['    ' + line for line in body]
        iter = 'BinaryFunction::inverse_iterator iter({0})'.format(self.value)
        return [
            'for ({0}; iter.ok(); iter.next()) {{'.format(iter),
            ] + body + [
            '}',
            ]

    def op_count(self):
        return 4.0 + 0.25 * OBJECT_COUNT * self.body.op_count()  # amortized

    def optimize(self):
        self.body.optimize()


class IterInvBinaryRange(Strategy):
    def __init__(self, fun, fixed, body):
        self.fun = fun.name
        self.value = str(Variable(fun))
        self.var1, self.var2 = fun.children
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

    def cpp_lines(self):
        body = []
        if self.lhs_fixed:
            body.append('oid_t {0} = iter.rhs();'.format(self.var2))
        else:
            body.append('oid_t {0} = iter.lhs();'.format(self.var1))
        body += self.body.cpp_lines()
        body = ['    ' + line for line in body]
        if self.lhs_fixed:
            iter = 'BinaryFunction::inv_range_iterator iter({0}, {1})'.format(
                    self.value, self.var2)
        else:
            iter = 'BinaryFunction::inv_range_iterator iter({0}, {1})'.format(
                    self.value, self.var1)
        return [
            'for ({0}; iter.ok(); iter.next()) {{'.format(iter),
            ] + body + [
            '}',
            ]

    def op_count(self):
        return 4.0 + 0.5 * self.body.op_count()  # amortized

    def optimize(self):
        self.body.optimize()


class Let(Strategy):
    def __init__(self, expr, body):
        assert isinstance(expr, Function)
        assert isinstance(body, Strategy)
        self.var = Variable(expr)
        self.expr = expr
        self.body = body

    def __repr__(self):
        return 'let {0}: {1}'.format(self.var, self.body)

    def cpp_lines(self):
        if self.expr.children:
            expr = str(self.expr)
        else:
            expr = 'signature::{0}()'.format(self.expr)
        return [
            'if (oid_t {0} = {1}) {{'.format(self.var, expr)
            ] + map(indent, self.body.cpp_lines()) + [
            '}'
            ]

    def op_count(self):
        return 1.0 + 0.5 * self.body.op_count()

    def optimize(self):
        self.body.optimize()


class Test(Strategy):
    def __init__(self, expr, body):
        assert isinstance(expr, Expression)
        assert isinstance(body, Strategy)
        self.expr = expr
        self.body = body

    def __repr__(self):
        return 'if {0}: {1}'.format(self.expr, self.body)

    def cpp_lines(self):
        body = map(indent, self.body.cpp_lines())
        return [
            'if ({0}) {{'.format(self.expr)
            ] + body + [
            '}',
            ]

    def op_count(self):
        return 1.0 + self.body.op_count()

    def optimize(self):
        self.body.optimize()


class Ensure(Strategy):
    def __init__(self, expr):
        assert isinstance(expr, Compound)
        self.expr = expr

    def __repr__(self):
        return 'ensure {0}'.format(self.expr)

    def cpp_lines(self):
        expr = self.expr
        assert len(expr.children) == 2
        lhs, rhs = expr.children
        if isinstance(lhs, Variable) and isinstance(rhs, Variable):
            args = ', '.join(map(str, expr.children))
            return ['ensure_{0}({1});'.format(expr.name.lower(), args)]
        else:
            assert isinstance(self.expr, Equation)
            if isinstance(lhs, Variable):
                name = rhs.name.lower()
                args = ', '.join(map(str, rhs.children))
                return ['ensure_{0}({1}, {2});'.format(name, args, lhs)]
            elif isinstance(rhs, Variable):
                name = lhs.name.lower()
                args = ', '.join(map(str, lhs.children))
                return ['ensure_{0}({1}, {2});'.format(name, args, rhs)]
            else:
                if rhs.name < lhs.name:
                    lhs, rhs = rhs, lhs
                name = '{0}_{1}'.format(lhs.name.lower(), rhs.name.lower())
                args = ', '.join(map(str, lhs.children + rhs.children))
                return ['ensure_{0}({1});'.format(name, args)]


    def op_count(self):
        fun_count = 0
        if isinstance(self.expr, Equation):
            lhs, rhs = self.expr.children
            fun_count += 1 if isinstance(lhs, Function) else 0
            fun_count += 1 if isinstance(rhs, Function) else 0

        return [1.0, 1.0 + 0.5 * 1.0, 2.0 + 0.75 * 1.0][fun_count]

    def optimize(self):
        pass


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
        return '{0} |- {1}'.format(
            ', '.join(map(str, self.antecedents)),
            ', '.join(map(str, self.succedents)))

    def ascii(self, indent = 0):
        top = '   '.join(map(str, self.antecedents))
        bot = '   '.join(map(str, self.succedents))
        bar = '-' * max(len(top), len(bot))
        diff = len(top) - len(bot)
        lpad = abs(diff) / 2
        rpad = diff - lpad
        if diff > 0 and bot:
            bot = ' ' * lpad + bot + ' ' * rpad
        if diff < 0 and top:
            top = ' ' * lpad + top + ' ' * rpad
        lines = [top, bar, bot]
        lines = filter(bool, lines)
        lines = map((' ' * indent).__add__, lines)
        return '\n'.join(lines)

    def html(self):
        antecedents = '   '.join(map(str, self.antecedents))
        succedents = '   '.join(map(str, self.succedents))
        bar = '&emdash;' * max(len(antecedents), len(succedents))
        lines = ['<code> <pre>']
        if antecedents:
            lines.append(antecedents)
        lines.append(bar)
        if succedents:
            lines.append(succedents)
        lines.append('</pre> </code>')
        return '\n'.join(lines)

    def get_vars(self):
        return union([e.get_vars()
                      for e in self.antecedents | self.succedents])

    def get_constants(self):
        return union([e.get_constants()
                      for e in self.antecedents | self.succedents])

    def get_signature(self):
        return union([e.get_signature()
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
        for expr in self.antecedents:
            if not expr.is_antecedent():
                return False
        for expr in self.succedents:
            if not expr.is_succedent():
                return False
        return True

    def contrapositives(self):
        if not self.succedents:
            TODO('allow empty succedents')
        elif len(self.succedents) > 1:
            TODO('allow multiple succedents')
        self_succedent = iter(self.succedents).next()
        result = set()
        for antecedent in self.antecedents:
            antecedents = set_without(self.antecedents, antecedent)
            succedents = antecedent.negated()
            for disjunct in self_succedent.negated():
                if disjunct.negated() & antecedents:
                    pass # contradiction
                else:
                    result.add(Sequent(
                        set_with(antecedents, disjunct),
                        succedents))
        return result

    def _atomic(self, bound=set()):
        '''
        Return a list of normalized sequents.
        '''
        if not self.succedents:
            TODO('allow empty succedents')
        elif len(self.succedents) > 1:
            result = set()
            for succedent in self.succedents:
                remaining = set_without(self.succedents, succedent)
                negated = union(set(s.negated()) for s in remaining)
                neg_neg = union(set(a.negated()) for a in self.antecedents)
                if not (negated & neg_neg):
                    antecedents = self.antecedents | negated
                    sequent = Sequent(antecedents, set([succedent]))
                    result |= set(sequent._atomic())
            return result

        self_succedent = iter(self.succedents).next()
        antecedents, succedent = self_succedent.as_succedent(bound)
        for a in self.antecedents:
            antecedents |= a.as_antecedent()
        return [Sequent(antecedents, set([succedent]))]

    def _normalized(self, bound=set()):
        result = self._atomic(bound)
        for neg in self.contrapositives():
            result += neg._atomic(bound)
        # TODO eliminate name-permutation duplicated sequents
        # TODO recognize symmetric functions
        # TODO recognize injective functions
        return result

    def get_events(self):
        events = set()
        for sequent in self._normalized():
            events |= sequent.antecedents
            # HACK to deal with Equation children
            succedent = iter(sequent.succedents).next()
            for child in succedent.children:
                if isinstance(child, Compound):
                    events.add(child)
        return events

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
            logger('optimizing over {0} versions'.format(len(ranked)))
            results.append(min(ranked))
        assert results, 'failed to compile'
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
        for part in self._normalized(bound):
            if atom in part.antecedents:
                ranked = map(rank, part._compile(context, bound))
                logger('optimizing over {0} versions'.format(len(ranked)))
                results.append(min(ranked))
        assert results, 'failed to compile_given: {0}'.format(atom)
        return results

    def _compile(self, context, bound):
        assert self._is_normal()
        antecedents = self.antecedents - context
        (succedent,) = list(self.succedents)
        return iter_compiled(antecedents, succedent, bound)


def iter_compiled(antecedents, succedent, bound):
    #print 'DEBUG', list(bound), '|', list(antecedents), '|-', succedent
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
            assert isinstance(a, Function), a
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

    # iterate forward
    for a in antecedents:
        # works for both Relation and Function antecedents
        if a.get_vars() & bound:
            for v in a.get_vars() - bound:
                bound_v = set_with(bound, v)
                for s in iter_compiled(antecedents, succedent, bound_v):
                    results.append(Iter(v, s))

    # iterate backward
    for a in antecedents:
        if isinstance(a, Function) and Variable(a) in bound:
            a_vars = a.get_vars()
            a_free = a_vars - bound
            a_bound = a_vars & bound
            arity = len(a.children)
            assert len(a_free) in [0, 1, 2]
            assert arity in [0, 1, 2]
            if arity and a_free:
                bound_v = bound | a_free
                antecedents_a = antecedents.copy()
                antecedents_a.remove(a)
                if arity == 1 and len(a_free) == 1:
                    for s in iter_compiled(antecedents_a, succedent, bound_v):
                        results.append(IterInvUnary(a, s))
                elif arity == 2 and len(a_free) == 1:
                    for s in iter_compiled(antecedents_a, succedent, bound_v):
                        (fixed,) = list(a.get_vars() - a_free)
                        results.append(IterInvBinaryRange(a, fixed, s))
                elif arity == 2 and len(a_free) == 2:
                    for s in iter_compiled(antecedents_a, succedent, bound_v):
                        results.append(IterInvBinary(a, s))

    if results:
        return results  # HEURISTIC iterate locally eagerly

    # iterate anything
    free = union([a.get_vars() for a in antecedents]) - bound
    for v in free:
        bound_v = set_with(bound, v)
        for s in iter_compiled(antecedents, succedent, bound_v):
            results.append(Iter(v, s))

    assert results
    return results


#-----------------------------------------------------------------------------
# Theory


class Theory:
    def __init__(self, sequents):
        self.sequents = sequents
        self.signature = {
            'nullary': [],
            'unary': [],
            'binary': [],
            'symmetric': [],
            }
        symbols = union([s.get_signature() for s in sequents])
        for c in symbols:
            if c in UNARY_FUNCTIONS:
                self.signature['unary'].append(c)
            elif c in BINARY_FUNCTIONS:
                self.signature['binary'].append(c)
            elif c in SYMMETRIC_FUNCTIONS:
                self.signature['symmetric'].append(c)
            else:
                self.signature['nullary'].append(c)
        for val in self.signature.itervalues():
            val.sort()

    def _write_signature(self, write, section):

        section('signature')
        write()

        write('namespace signature {')
        write()

        write('Carrier carrier;')
        write()

        write('BinaryRelation LESS(carrier);')
        write('BinaryRelation NLESS(carrier);')
        write()

        for arity in ['nullary', 'unary', 'binary', 'symmetric']:
            Arity = arity.capitalize()
            if self.signature[arity]:
                for name in self.signature[arity]:
                    write('{0}Function {1}(carrier);'.format(Arity, name))
                write()

        write('} // namespace signature')
        write('using namespace signature;')
        write()

    def _write_ensurers(self, write, section):

        section('ensurers')
        write()

        write(dedent('''
        inline void ensure_equal (oid_t lhs, oid_t rhs)
        {
            if (lhs != rhs) {
                oid_t dep = lhs < rhs ? lhs : rhs;
                oid_t rep = lhs < rhs ? rhs : lhs;
                carrier.merge(dep, rep);
                schedule(MergeTask(dep));
            }
        }

        // TODO most uses of this can be vectorized
        // TODO use .contains_Lx/.contains_Rx based on iterator direction
        inline void ensure_less (oid_t lhs, oid_t rhs)
        {
            // TODO do this more atomically
            if (not LESS(lhs, rhs)) {
                LESS.insert(lhs, rhs);
                schedule(PositiveOrderTask(lhs, rhs));
            }
        }

        // TODO most uses of this can be vectorized
        // TODO use .contains_Lx/.contains_Rx based on iterator direction
        inline void ensure_nless (oid_t lhs, oid_t rhs)
        {
            // TODO do this more atomically
            if (not NLESS(lhs, rhs)) {
                NLESS.insert(lhs, rhs);
                schedule(NegativeOrderTask(lhs, rhs));
            }
        }
        ''').strip())
        write()

        arities = [('unary', 1), ('binary', 2), ('symmetric', 2)]
        functions = [(name, arity, argc)
                     for arity, argc in arities
                     for name in self.signature[arity]]

        def oid_t(x):
            return 'oid_t {0}'.format(x)

        for name, arity, argc in functions:
            vars_ = ['key'] if argc == 1 else ['lhs', 'rhs']
            write(dedent('''
            inline void ensure_{name} ({typed_args}, oid_t val)
            {{
                if (oid_t old_val = {NAME}({args})) {{
                    ensure_equal(old_val, val);
                }} else {{
                    {NAME}.insert({args}, val);
                    schedule({Arity}FunctionTask({NAME}, {args}));
                }}
            }}
            ''')
            .format(
                name=name.lower(),
                NAME=name,
                args=', '.join(vars_),
                typed_args=', '.join(map(oid_t, vars_)),
                Arity=arity.capitalize(),
                )
            .strip())
            write()

        for name1, arity1, argc1 in functions:
            for name2, arity2, argc2 in functions:
                if name2 > name1:
                    continue

                vars1 = ['key1'] if argc1 == 1 else ['lhs1', 'rhs1']
                vars2 = ['key2'] if argc2 == 1 else ['lhs2', 'rhs2']
                write(dedent('''
                inline void ensure_{name1}_{name2} (
                    {typed_args1},
                    {typed_args2})
                {{
                    if (oid_t val1 = {NAME1}({args1})) {{
                        ensure_{name2}({args2}, val1);
                    }} else {{
                        if (oid_t val2 = {NAME2}({args2})) {{
                            {NAME1}.insert({args1}, val2);
                            schedule({Arity1}FunctionTask({NAME1}, {args1}));
                        }}
                    }}
                }}
                ''')
                .format(
                    name1=name1.lower(),
                    name2=name2.lower(),
                    NAME1=name1,
                    NAME2=name2,
                    args1=', '.join(vars1),
                    args2=', '.join(vars2),
                    typed_args1=', '.join(map(oid_t, vars1)),
                    typed_args2=', '.join(map(oid_t, vars2)),
                    Arity1=arity.capitalize(),
                    Arity2=arity2.capitalize(),
                    )
                .strip())
                write()

    def _write_full_tasks(self, write, section):

        full_tasks = []
        for sequent in self.sequents:
            full_tasks += sequent.compile()
        full_tasks.sort(key=(lambda (cost, _): cost))
        type_count = len(full_tasks)

        section('full tasks')
        write(dedent('''

        const size_t g_type_count = {type_count};
        std::vector<std::atomic_flag> g_clean_state(g_type_count, true);

        void set_state_dirty ()
        {{
            for (auto & state : g_clean_state) {{
                state.clear();
            }}
        }}

        void execute (const CleanupTask & task)
        {{
            // HACK
            // TODO find a better cleanup scheduling policy
            size_t next_type = (task.type + 1) % g_type_count;
            if (task.type >= g_type_count) {{
                schedule(CleanupTask(0));
            }}
            if (not g_clean_state[task.type].test_and_set()) {{
                schedule(CleanupTask(next_type));
                return;
            }}

            switch (task.type)
            {{
        ''').rstrip().format(
            type_count=type_count
            ))

        for i, (cost, strategy) in enumerate(full_tasks):
            write()
            write('    case {0}: {{ // cost = {1}'.format(i, cost))
            for line in strategy.cpp_lines():
                write('        ' + line)
            write('    } break;')

        write(dedent('''
            default: POMAGMA_ERROR("bad cleanup type" << task.type);
            }

            schedule(CleanupTask(next_type));
        }
        '''))

    def _write_event_tasks(self, write, section):

        section('event tasks')
        write()

        event_tasks = {}
        for sequent in self.sequents:
            for event in sequent.get_events():
                tasks = event_tasks.setdefault(event.name, [])
                tasks += sequent.compile_given(event)

        event_tasks = sorted(
                event_tasks.items(),
                key=(lambda (name, tasks): (len(tasks), len(name), name)))
        for event, tasks in event_tasks:
            tasks.sort(key=(lambda (cost, _): cost))
            Type = TYPE_TABLE.get(event, 'NullaryFunction')

            write(dedent('''
            void execute (const {Type}Task & task)
            {{
            ''').rstrip().format(
                Type=Type
                ))

            for cost, strategy in tasks:
                write()
                write('    // cost = {0}'.format(cost))
                for line in strategy.cpp_lines():
                    write('    ' + line)

            write('}')

    def cpp_lines(self):
        lines = []

        def write(line_with_newlines=''):
            for line in line_with_newlines.split('\n'):
                lines.append(line)

        def section(name):
            write()
            write('//' + '-' * 76)
            write('// {0}'.format(name))

        self._write_signature(write, section)
        self._write_ensurers(write, section)
        self._write_full_tasks(write, section)
        self._write_event_tasks(write, section)

        return lines
