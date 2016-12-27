import re

from pomagma.compiler import signature
from pomagma.compiler.signature import ARITY_TABLE
from pomagma.compiler.util import inputs, memoize_make, sortedset, union

re_name = re.compile('[a-zA-Z][a-zA-Z0-9_]*$')
re_space = re.compile('[ _]+')


@memoize_make
class Expression(object):
    __slots__ = [
        '_name', '_args', '_arity', '_polish', '_hash', '_sort', '_var',
        '_vars', '_consts', '_terms',
    ]

    def __init__(self, name, *args):
        assert isinstance(name, str), type(name)
        assert re_name.match(name), name
        arity = signature.get_arity(name)
        assert len(args) == signature.get_nargs(arity), (args, arity)
        for arg in args:
            assert isinstance(arg, Expression), arg
        self._name = intern(name)
        self._args = args
        self._arity = arity
        self._polish = intern(' '.join([name] + [arg._polish for arg in args]))
        self._hash = hash(self._polish)
        self._sort = (len(self._polish), self._polish)
        # all other fields are lazily initialized
        self._var = None
        self._vars = None
        self._consts = None
        self._terms = None

    @property
    def name(self):
        return self._name

    @property
    def args(self):
        return self._args

    @property
    def arity(self):
        return self._arity

    @property
    def polish(self):
        return self._polish

    @property
    def var(self):
        if self._var is None:
            if self._arity == 'Variable':
                self._var = self
            elif self._arity == 'NullaryFunction':
                self._var = Expression.make(self._name + '_')
            elif self._arity in signature.FUNCTION_ARITIES:
                var = re_space.sub('_', self._polish.rstrip('_'))
                self._var = Expression.make(var)
        return self._var

    @property
    def vars(self):
        if self._vars is None:
            if self._arity == 'Variable':
                self._vars = set([self])
            elif self._arity == 'NullaryFunction':
                self._vars = set()
            elif self._arity in signature.FUNCTION_ARITIES:
                self._vars = union(a.vars for a in self._args)
            else:
                self._vars = union(a.vars for a in self._args)
            self._vars = sortedset(self._vars)
        return self._vars

    @property
    def consts(self):
        if self._consts is None:
            if self.is_fun() and not self._args:
                self._consts = sortedset([self])
            else:
                self._consts = sortedset(union(a.consts for a in self._args))
        return self._consts

    @property
    def terms(self):
        if self._terms is None:
            self._terms = union(a.terms for a in self._args)
            if self.is_term():
                self._terms.add(self)
            self._terms = sortedset(self._terms)
        return self._terms

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        assert isinstance(other, Expression), other
        return self._polish == other._polish

    def __lt__(self, other):
        return self._sort < other._sort

    def __str__(self):
        return self._polish

    def __repr__(self):
        return self._polish

    def is_var(self):
        return signature.is_var(self.name)

    def is_fun(self):
        return signature.is_fun(self.name)

    def is_rel(self):
        return signature.is_rel(self.name)

    def is_con(self):
        return signature.is_con(self.name)

    def is_term(self):
        return signature.is_term(self.name)

    def substitute(self, var, defn):
        assert isinstance(var, Expression) and var.is_var()
        assert isinstance(defn, Expression)
        if var not in self.vars:
            return self
        elif self.is_var():
            return defn
        else:
            return Expression.make(
                self.name,
                *(arg.substitute(var, defn) for arg in self._args))

    def swap(self, var1, var2):
        assert isinstance(var1, Expression) and var1.is_var()
        assert isinstance(var2, Expression) and var2.is_var()
        if var1 not in self.vars and var2 not in self.vars:
            return self
        elif self == var1:
            return var2
        elif self == var2:
            return var1
        else:
            return Expression.make(
                self.name,
                *(arg.swap(var1, var2) for arg in self._args))

    def permute_symbols(self, perm):
        assert isinstance(perm, dict)
        name = '_'.join(perm.get(n, n) for n in self.name.split('_'))
        args = (a.permute_symbols(perm) for a in self._args)
        return Expression.make(name, *args)


def Expression_0(name):
    return Expression.make(name)


def Expression_1(name):
    return lambda x: Expression.make(name, x)


def Expression_2(name):
    return lambda x, y: Expression.make(name, x, y)


class NotNegatable(Exception):
    pass


def try_negate_name(pos):
    assert pos in ARITY_TABLE
    neg = pos[1:] if pos.startswith('N') else 'N' + pos
    if neg not in ARITY_TABLE or ARITY_TABLE[neg] != ARITY_TABLE[pos]:
        raise NotNegatable
    return neg


@inputs(Expression)
def try_get_negated(expr):
    """Returns a disjunction."""
    if expr.name == 'EQUAL':
        lhs, rhs = expr.args
        return set([Expression.make('NLESS', lhs, rhs),
                    Expression.make('NLESS', rhs, lhs)])
    else:
        neg_name = try_negate_name(expr.name)
        return set([Expression.make(neg_name, *expr.args)])
