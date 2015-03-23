import itertools
from pomagma.compiler.expressions import Expression
from pomagma.compiler.util import TODO
from pomagma.compiler.util import inputs
from pomagma.compiler.util import set_without
from pomagma.compiler.util import union


class Sequent(object):

    def __init__(self, antecedents, succedents):
        antecedents = frozenset(antecedents)
        succedents = frozenset(succedents)
        for expr in antecedents | succedents:
            assert isinstance(expr, Expression)
        self._antecedents = antecedents
        self._succedents = succedents
        self._hash = hash((antecedents, succedents))
        self._str = None
        self.debuginfo = {}

    @property
    def antecedents(self):
        return self._antecedents

    @property
    def succedents(self):
        return self._succedents

    @property
    def optional(self):
        return all(s.name == 'OPTIONALLY' for s in self.succedents)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return (self._antecedents == other._antecedents and
                self._succedents == other._succedents)

    def __lt__(self, other):
        s = str(self)
        o = str(other)
        return (len(s), s) < (len(o), o)

    def __str__(self):
        if self._str is None:
            self._str = '{0} |- {1}'.format(
                ', '.join(map(str, self.antecedents)),
                ', '.join(map(str, self.succedents)))
        return self._str

    def __repr__(self):
        return 'Sequent({0})'.format(self)

    def ascii(self, indent=0):
        top = '   '.join(map(str, self.antecedents))
        bot = '   '.join(map(str, self.succedents))
        width = max(len(top), len(bot))
        top = top.center(width)
        bot = bot.center(width)
        bar = '-' * width
        lines = [top, bar, bot]
        lines = filter(bool, lines)
        lines = map((' ' * indent).__add__, lines)
        return '\n'.join(lines)

    @property
    def vars(self):
        return union(s.vars for s in self.antecedents | self.succedents)


@inputs(Expression)
def as_atom(expr):
    args = [arg.var for arg in expr.args]
    return Expression(expr.name, *args)


class NotNegatable(Exception):
    pass


@inputs(Expression)
def get_negated(expr):
    'Returns a disjunction'
    if expr.name == 'LESS':
        return set([Expression('NLESS', *expr.args)])
    elif expr.name == 'NLESS':
        return set([Expression('LESS', *expr.args)])
    elif expr.name == 'EQUAL':
        lhs, rhs = expr.args
        return set([Expression('NLESS', lhs, rhs),
                    Expression('NLESS', rhs, lhs)])
    else:
        raise NotNegatable(expr.name)


@inputs(Expression, Expression)
def pairwise_consistent(p, q):
    if p.name == 'EQUAL':
        if q.name == 'NLESS':
            return set(p.args) != set(q.args)
    elif p.name == 'LESS':
        if q.name == 'NLESS':
            return p.args != q.args
    elif q.name == 'NLESS':
        if p.name == 'EQUAL':
            return set(p.args) != set(q.args)
        elif p.name == 'LESS':
            return p.args != q.args
    return True


def all_consistent(exprs):
    return all(pairwise_consistent(p, q) for p in exprs for q in exprs)


@inputs(Expression)
def as_antecedents(expr, bound):
    antecedents = set()
    while expr.name in ['OPTIONALLY', 'NONEGATE']:
        expr = expr.args[0]
    if expr.arity != 'Variable':
        atom = as_atom(expr)
        if not (atom.var in bound and all(arg in bound for arg in atom.args)):
            antecedents.add(atom)
        for arg in expr.args:
            antecedents |= as_antecedents(arg, bound)
    return antecedents


@inputs(Expression)
def as_succedent(expr, bound):
    while expr.name in ['OPTIONALLY', 'NONEGATE']:
        expr = expr.args[0]
    antecedents = set()
    if expr.arity == 'Equation':
        args = []
        for arg in expr.args:
            if arg.var in bound:
                args.append(arg.var)
            else:
                args.append(as_atom(arg))
                for argarg in arg.args:
                    antecedents |= as_antecedents(argarg, bound)
        succedent = Expression(expr.name, *args)
    else:
        assert expr.args, expr.args
        succedent = as_atom(expr)
        for arg in expr.args:
            antecedents |= as_antecedents(arg, bound)
    return antecedents, succedent


@inputs(Sequent)
def get_pointed(seq):
    '''
    Return a set of sequents each with a single succedent.
    '''
    result = set()
    if len(seq.succedents) == 1:
        for succedent in seq.succedents:
            if succedent.name != 'OPTIONALLY':
                result.add(seq)
    elif len(seq.succedents) > 1:
        for succedent in seq.succedents:
            remaining = set_without(seq.succedents, succedent)
            try:
                neg_remaining = map(get_negated, remaining)
            except NotNegatable:
                continue
            for negated in itertools.product(*neg_remaining):
                antecedents = seq.antecedents | set(negated)
                if all_consistent(antecedents):
                    result.add(Sequent(antecedents, set([succedent])))
    else:
        TODO('allow empty succedents')
    return result


@inputs(Sequent)
def get_atomic(seq, bound=set()):
    '''
    Return a set of normal sequents.
    Atoms whose every variable is bound are excluded from antecedents.
    '''
    result = set()
    for pointed in get_pointed(seq):
        improper_succedent = iter(pointed.succedents).next()
        antecedents, succedent = as_succedent(improper_succedent, bound)
        for a in pointed.antecedents:
            antecedents |= as_antecedents(a, bound)
        result.add(Sequent(antecedents, set([succedent])))
    return result


@inputs(Sequent)
def get_contrapositives(seq):
    result = set()
    if len(seq.succedents) == 1:
        succedent = iter(seq.succedents).next()
        try:
            neg_succedents = get_negated(succedent)
        except NotNegatable:
            return result
        for antecedent in seq.antecedents:
            try:
                neg_antecedents = get_negated(antecedent)
            except NotNegatable:
                continue
            for neg_succedent in neg_succedents:
                antecedents = set(seq.antecedents)
                antecedents.remove(antecedent)
                antecedents.add(neg_succedent)
                if all_consistent(antecedents):
                    result.add(Sequent(antecedents, neg_antecedents))
        return result
    elif len(seq.succedents) > 1:
        TODO('allow multiple succedents')
    else:
        TODO('allow empty succedents')


@inputs(Sequent)
def normalize(seq, bound=set()):
    '''
    Return a set of normal sequents, closed under contrapositive.
    Atoms whose every variable is bound are excluded from antecedents.
    '''
    if seq.optional:
        return set()
    result = get_atomic(seq, bound)
    for contra in get_contrapositives(seq):
        result |= get_atomic(contra, bound)
    assert result, 'failed to normalize {0} binding {1}'.format(seq, bound)
    return result


@inputs(Sequent)
def assert_normal(seq):
    assert len(seq.succedents) == 1
    for expr in seq.antecedents:
        for arg in expr.args:
            assert arg.arity == 'Variable', arg
    for expr in seq.succedents:
        if expr.arity == 'Equation':
            for arg in expr.args:
                for arg_arg in arg.args:
                    assert arg_arg.arity == 'Variable', arg_arg
        else:
            for arg in expr.args:
                assert arg.arity == 'Variable', arg
