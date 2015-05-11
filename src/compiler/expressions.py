import re
from pomagma.compiler import signature
from pomagma.compiler.signature import ARITY_TABLE
from pomagma.compiler.util import inputs
from pomagma.compiler.util import memoize_make
from pomagma.compiler.util import sortedset
from pomagma.compiler.util import union

re_name = re.compile('[a-zA-Z][a-zA-Z_]*$')
re_space = re.compile('[ _]+')


@memoize_make
class Expression(object):
    __slots__ = [
        '_name', '_args', '_arity', '_polish', '_hash', '_var',
        '_vars', '_consts', '_terms',
    ]

    def __init__(self, name, *args):
        assert isinstance(name, str), name
        assert re_name.match(name), name
        arity = signature.get_arity(name)
        assert len(args) == signature.get_nargs(arity), (args, arity)
        for arg in args:
            assert isinstance(arg, Expression), arg
        self._name = name
        self._args = args
        self._arity = arity
        self._polish = ' '.join([name] + [arg._polish for arg in args])
        self._hash = hash(self._polish)

        if arity == 'Variable':
            self._var = self
            self._vars = set([self])
        elif arity == 'NullaryFunction':
            self._var = Expression.make(name + '_')
            self._vars = set()
        elif arity in signature.FUNCTION_ARITIES:
            var = re_space.sub('_', self._polish.rstrip('_'))
            self._var = Expression.make(var)
            self._vars = union(arg.vars for arg in args)
        else:
            self._var = None
            self._vars = union(arg.vars for arg in args)
        self._vars = sortedset(self._vars)

        if self.is_fun() and not self.args:
            self._consts = sortedset([self])
        else:
            self._consts = sortedset(union(arg.consts for arg in self.args))

        self._terms = union(arg.terms for arg in self.args)
        if self.is_term():
            self._terms.add(self)
        self._terms = sortedset(self._terms)

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
        return self._var

    @property
    def vars(self):
        return self._vars

    @property
    def consts(self):
        return self._consts

    @property
    def terms(self):
        return self._terms

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        assert isinstance(other, Expression), other
        return self._polish == other._polish

    def __lt__(self, other):
        s = self._polish
        o = other._polish
        return (len(s), s) < (len(o), o)

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
                *(arg.substitute(var, defn) for arg in self.args))

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
                *(arg.swap(var1, var2) for arg in self.args))

    def permute_symbols(self, perm):
        assert isinstance(perm, dict)
        name = '_'.join(perm.get(n, n) for n in self.name.split('_'))
        args = (arg.permute_symbols(perm) for arg in self.args)
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
    'Returns a disjunction'
    if expr.name == 'EQUAL':
        lhs, rhs = expr.args
        return set([Expression.make('NLESS', lhs, rhs),
                    Expression.make('NLESS', rhs, lhs)])
    else:
        neg_name = try_negate_name(expr.name)
        return set([Expression.make(neg_name, *expr.args)])
