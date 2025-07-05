from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_corpus
from pomagma.compiler.util import inputs
from pomagma.util import TODO

HOLE = Expression("HOLE")


class Corpus:
    """
    Corpus is a general-recursive set of definitions with holes.
    """

    def __init__(self):
        self._defs = {}

    def load(self, filename):
        with open(filename) as f:
            self._defs = parse_corpus(f, filename=filename)

    def dump(self, filename):
        with open(filename, "w") as f:
            f.write(f"# Corpus written by {__file__}")
            for var, expr in sorted(self._defs.items()):
                assert isinstance(var, str), var
                assert isinstance(expr, Expression), expr
                f.write(f"\nEQUAL {var} {expr}")

    def __getitem__(self, var):
        assert isinstance(var, Expression), var
        assert var.is_var(), var
        return self._defs.getitem(var, HOLE)

    def __setitem__(self, var, expr):
        assert isinstance(var, Expression), var
        assert isinstance(expr, Expression), expr
        assert var.is_var(), var
        if expr is HOLE:
            self._defs.pop(var, None)
        else:
            self._defs[var] = expr

    def __iter__(self):
        return iter(list(self._defs.items()))

    def insert(self, key, value="HOLE"):
        var = Expression(key)
        expr = Expression(value)
        self[var] = expr


@inputs(Corpus)
def assess(corpus):
    TODO("report belief of validity of corpus")


@inputs(Corpus)
def refine(corpus, result_count=(2**5), search_count=(2**15)):
    TODO("propose candidate joint hole-filling refinements of a corpus")
