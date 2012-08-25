import re
from pomagma.util import TODO, inputs
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
        self._polish = ' '.join([name] + map(get_polish, args))
        self._hash = hash(self._polish)
        if arity == 'Variable':
            self._varname = name
        elif arity == 'NullaryFunction':
            self._varname = name + '_'
        else:
            self._varname = re.sub('[ _]+', '_', self.polish)
        assert signature.is_var(self._varname)

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
    def varname(self):
        return self._varname

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._polish == other._polish

    def __str__(self):
        return self._polish


@inputs(Expression)
def get_polish(expr):
    return expr.polish


@inputs(Expression)
def as_variable(expr):
    if expr.arity == 'Variable':
        return expr
    else:
        return Expression(expr.varname)






def pretty(expr):
    name = expr['name']
    args = expr['args']
    if args:
        return '{0}({1})'.format(name, ', '.join(map(pretty, args)))
    else:
        return name


def get_signature(expr, result=None):
    if result is None:
        result = set()
    name = expr['name']
    if not signature.is_var(name):
        result.add(name)
        for arg in expr['args']:
            get_signature(arg, result)
    return result


def get_vars(expr, result=None):
    if result is None:
        result = set()
    name = expr['name']
    if signature.is_var(name):
        result.add(name)
    else:
        for arg in expr['args']:
            get_vars(arg, result)
    return result


def get_constants(expr, result=None):
    if result is None:
        result = set()
    name = expr['name']
    args = expr['args']
    if args:
        for arg in args:
            get_constants(arg, result)
    elif not signature.is_var(name):
        result.add(name)
    return result


def as_atom(expr):
    return {'name': expr['name'],
            'args': map(as_variable, expr['args'])}


def as_antecedent(expr, result=None):
    if result is None:
        result = []
    name = expr['name']
    if not signature.is_var(name):
        result.append(as_atom(expr))
        for arg in args:
            as_antecedent(arg, result)
