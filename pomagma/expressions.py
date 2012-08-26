import re
from pomagma.util import TODO, inputs, union
from pomagma import signature


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
        elif arity == 'NullaryFunction':
            self._var = Expression(name + '_')
        elif arity in ['InjectiveFunction', 'BinaryFunction', 'SymmetricFunction']:
            var = re.sub('[ _]+', '_', self.polish).rstrip('_')
            self._var = Expression(var)
        else:
            self._var = None

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

    def get_vars(self):
        if self.is_var():
            return set([self])
        else:
            return union(arg.get_vars() for arg in self.args)
