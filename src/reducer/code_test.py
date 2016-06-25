from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import VAR, APP, JOIN, FUN, LET
from pomagma.reducer.code import free_vars
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s

x = VAR('x')
y = VAR('y')
z = VAR('z')

EXAMPLES = [
    ('HOLE', HOLE),
    ('TOP', TOP),
    ('BOT', BOT),
    ('I', I),
    ('K', K),
    ('B', B),
    ('C', C),
    ('S', S),
    ('VAR x', x),
    ('APP I K', APP(I, K)),
    ('JOIN K APP K I', JOIN(K, APP(K, I))),
    ('APP APP I K JOIN B C', APP(APP(I, K), JOIN(B, C))),
    ('FUN VAR x APP VAR x VAR x', FUN(x, APP(x, x))),
    ('LET VAR x I APP I I', LET(x, I, APP(I, I))),
]


@for_each(EXAMPLES)
def test_parse(string, code):
    actual_string = serialize(code)
    assert actual_string == string


@for_each(EXAMPLES)
def test_serialize(string, code):
    actual_code = parse(string)
    assert actual_code == code


@for_each([
    (I, []),
    (x, [x]),
    (APP(I, x), [x]),
    (APP(x, x), [x]),
    (APP(x, y), [x, y]),
    (APP(x, JOIN(y, APP(K, z))), [x, y, z]),
])
def test_free_vars(code, free):
    assert free_vars(code) == set(free)


alphabet = '_abcdefghijklmnopqrstuvwxyz'
s_vars = s.builds(VAR,
    s.builds(str, s.text(alphabet=alphabet, min_size=1, average_size=5)))
s_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(HOLE),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
)


def s_terms_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(JOIN, terms, terms),
        s.builds(FUN, s_vars, terms),
        s.builds(LET, s_vars, terms, terms),
    )


s_terms = s.recursive(s_atoms, s_terms_extend, max_leaves=100)


@hypothesis.given(s_terms)
@hypothesis.settings(max_examples=1000)
def test_serialize_parse(code):
    string = serialize(code)
    assert isinstance(string, str)
    actual_code = parse(string)
    assert actual_code == code
