from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, APP, JOIN, VAR
from pomagma.reducer.code import free_vars
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
from pomagma.util.testing import for_each

EXAMPLES = [
    ('I', I),
    ('K', K),
    ('B', B),
    ('C', C),
    ('S', S),
    ('TOP', TOP),
    ('BOT', BOT),
    ('APP I K', APP(I, K)),
    ('JOIN K APP K I', JOIN(K, APP(K, I))),
    ('APP APP I K JOIN B C', APP(APP(I, K), JOIN(B, C))),
]


@for_each(EXAMPLES)
def test_parse(string, code):
    actual_string = serialize(code)
    assert actual_string == string


@for_each(EXAMPLES)
def test_serialize(string, code):
    actual_code = parse(string)
    assert actual_code == code


x = VAR('x')
y = VAR('y')
z = VAR('z')


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
