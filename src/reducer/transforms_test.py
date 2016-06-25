from pomagma.reducer.code import I, K, B, C, S, VAR, APP, JOIN
from pomagma.reducer.transforms import abstract
from pomagma.util.testing import for_each

x = VAR('x')
y = VAR('y')
z = VAR('z')


@for_each([
    (x, x, I),
    (x, y, APP(K, y)),
    (x, I, APP(K, I)),
    (x, APP(x, x), APP(APP(S, I), I)),
    (x, APP(x, y), APP(APP(C, I), y)),
    (x, APP(y, x), y),
    (x, APP(y, APP(z, x)), APP(APP(B, y), z)),
    (x, JOIN(x, x), JOIN(I, I)),
    (x, JOIN(x, y), JOIN(I, APP(K, y))),
    (x, JOIN(y, x), JOIN(APP(K, y), I)),
    (x, JOIN(y, z), APP(K, JOIN(y, z))),
])
def test_abstract(var, body, expected_abs):
    actual_abs = abstract(var, body)
    assert actual_abs == expected_abs
