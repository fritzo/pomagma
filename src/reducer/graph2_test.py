import pytest

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
    pytest.mark.xfail((x, y, x, y)),
    (x, y, y, y),
    (x, y, z, z),
])
def test_substitute(old, new, node, expected):
    old = old.copy()
    new = new.copy()
    node = node.copy()
    expected = expected.copy()
    actual = substitute(old, new, node)
    assert actual == expected, '{} vs {}'.format(actual, expected)


@for_each([
    (FUN(x, x), FUN(x, x), False),
    pytest.mark.xfail((APP(FUN(x, x), y), y, True)),
])
def test_try_beta_step(node, expected_node, expected_whether):
    actual_node = node.copy()
    assert try_beta_step(actual_node) is expected_whether
    assert actual_node == expected_node, '{} vs {}'.format(
        actual_node,
        expected_node)
