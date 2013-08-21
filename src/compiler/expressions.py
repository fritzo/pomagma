import re
from pomagma.compiler.util import union
from pomagma.compiler import signature


class Expression(object):

    def __init__(self, name, *args):
        assert isinstance(name, str)
        assert re.match('[a-zA-Z][a-zA-Z_]*$', name),\
            'invalid name: {0}'.format(name)
        args = list(args)
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
            self._var = Expression(name + '_')
            self._vars = set()
        elif arity in [
                'InjectiveFunction',
                'BinaryFunction',
                'SymmetricFunction',
        ]:
            var = re.sub('[ _]+', '_', self.polish).rstrip('_')
            self._var = Expression(var)
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
            return union([arg.consts for arg in self.args])

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        assert isinstance(other, Expression), other
        return self._polish == other._polish

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

    def substitute(self, var, defn):
        assert isinstance(var, Expression)
        assert isinstance(defn, Expression)
        assert var.is_var()
        if var not in self.vars:
            return self
        elif self.is_var():
            return defn
        else:
            return Expression(
                self.name,
                *[arg.substitute(var, defn) for arg in self.args])
