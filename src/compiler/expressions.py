import re
from pomagma.compiler import signature
from pomagma.compiler.signature import ARITY_TABLE
from pomagma.compiler.util import inputs
from pomagma.compiler.util import memoize_args
from pomagma.compiler.util import union

re_name = re.compile('[a-zA-Z][a-zA-Z_]*$')
re_space = re.compile('[ _]+')


class Expression(object):
    __slots__ = [
        '_name', '_args', '_arity', '_polish', '_hash', '_var', '_vars',
    ]

    def __init__(self, name, *args):
        assert isinstance(name, str)
        assert re_name.match(name), name
        arity = signature.get_arity(name)
        assert len(args) == signature.get_nargs(arity)
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
            self._var = get_expression(name + '_')
            self._vars = set()
        elif arity in signature.FUNCTION_ARITIES:
            var = re_space.sub('_', self._polish.rstrip('_'))
            self._var = get_expression(var)
            self._vars = union(arg.vars for arg in args)
        else:
            self._var = None
            self._vars = union(arg.vars for arg in args)

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
        return self._vars.copy()

    @property
    def consts(self):
        if self.is_fun() and not self.args:
            return set([self])
        else:
            return union(arg.consts for arg in self.args)

    @property
    def terms(self):
        result = union(arg.terms for arg in self.args)
        if self.is_term():
            result.add(self)
        return result

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
        return self.is_var() or self.is_fun()

    def substitute(self, var, defn):
        assert isinstance(var, Expression)
        assert isinstance(defn, Expression)
        assert var.is_var()
        if var not in self.vars:
            return self
        elif self.is_var():
            return defn
        else:
            return get_expression(
                self.name,
                *[arg.substitute(var, defn) for arg in self.args])


@memoize_args
def get_expression(*args):
    return Expression(*args)


def Expression_0(name):
    return get_expression(name)


def Expression_1(name):
    return lambda x: get_expression(name, x)


def Expression_2(name):
    return lambda x, y: get_expression(name, x, y)


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
        return set([get_expression('NLESS', lhs, rhs),
                    get_expression('NLESS', rhs, lhs)])
    else:
        neg_name = try_negate_name(expr.name)
        return set([get_expression(neg_name, *expr.args)])
