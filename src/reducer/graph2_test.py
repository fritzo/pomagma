from pomagma.reducer.graph2 import APP, FUN, NVAR, substitute, try_beta_step
from pomagma.util.testing import for_each

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


@for_each([x, y, z, APP(x, y)])
def test_eq(x):
    assert x == x


@for_each([
    (x, y),
    (APP(x, x), APP(x, y)),
    (APP(x, x), APP(y, x)),
])
def test_neq(x, y):
    assert x != y


@for_each([
    (x, y, x, y),
    (x, y, y, y),
    (x, y, z, z),
])
def test_substitute(old, new, node, expected):
    actual = substitute(old, new, node)
    assert actual == expected, '{} vs {}'.format(actual, expected)


@for_each([
    (x, x, False),
    (APP(x, x), APP(x, x), False),
    (FUN(x, x), FUN(x, x), False),
    (FUN(x, y), FUN(x, y), False),
    (APP(FUN(x, y), z), y, True),
    (APP(FUN(x, x), y), y, True),
    (APP(FUN(x, x), y), y, True),
    (APP(APP(FUN(x, x), z), y), APP(z, y), True),
    (APP(y, APP(FUN(x, x), z)), APP(y, z), True),
    (APP(APP(x, APP(FUN(x, x), y)), z), APP(APP(x, y), z), True),
    (APP(APP(x, z), APP(FUN(x, x), y)), APP(APP(x, z), y), True),
    (
        APP(APP(x, APP(FUN(x, x), y)), APP(FUN(x, x), z)),
        APP(APP(x, y), APP(FUN(x, x), z)),
        True,
    ),
])
def test_try_beta_step(node, expected_node, expected_whether):
    actual_node = node.copy()
    assert try_beta_step(actual_node) is expected_whether
    assert actual_node == expected_node, '{} vs {}'.format(
        actual_node,
        expected_node)
