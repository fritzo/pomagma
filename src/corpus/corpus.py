from pomagma.compiler.expressions import Expression
from pomagma.compiler.util import inputs
from pomagma.util import TODO
import re

HOLE = Expression.make('HOLE')


class Corpus(object):
    '''
    Corpus is a general-recursive set of definitions.
    '''
    def __init__(self):
        self._defs = {}

    def clear(self):
        self._defs = {}

    def load(self, filename):
        self.clear()
        with open(filename) as f:
            for line in f:
                line = re.sub('#.*', '', line).strip()
                if line:
                    assert line.startswith('EQUAL '), line
                    _, name, value = line.split(' ', 2)
                    self._defs[name] = Expression.make(value)

    def dump(self, filename):
        with open(filename, 'w') as f:
            f.write('# Corpus written by {}\n'.format(__file__))
            for name, expr in sorted(self._defs.iteritems()):
                assert isinstance(name, basestring), name
                assert isinstance(expr, Expression), expr
                f.write('EQUAL {} {}\n'.format(name, expr.polish))

    def __getitem__(self, name):
        return self._defs.getitem(name, HOLE)

    def __setitem__(self, name, value):
        expr = Expression.make(value)
        if expr is HOLE:
            self._defs.pop(name, None)
        else:
            self._defs[name] = value


@inputs(Corpus, basestring, basestring)
def define(corpus, name, value='HOLE'):
    expr = Expression.make(value)
    assert not expr.is_var(), 'Invalid non-strict definition'
    corpus[name] = expr


@inputs(Corpus, basestring)
def refine(corpus, name):
    TODO('propose candidate hole-fillings of a partially-defined term')


@inputs(Corpus)
def verify(corpus):
    TODO('report belief of validity of corpus')
