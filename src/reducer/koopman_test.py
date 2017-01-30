from pomagma.reducer.koopman import (APP, ATOM, BOT, TOP, B, C, I, K, S,
                                     print_to_depth, try_beta_step)
from pomagma.util.testing import for_each

x = ATOM('x')
y = ATOM('y')
z = ATOM('z')

BETA_STEP_EXAMPLES = [
    (x, False, x),
    (APP(x, y), False, APP(x, y)),
    (TOP, False, TOP),
    (APP(TOP, x), True, TOP),
    (APP(x, APP(TOP, y)), True, APP(x, TOP)),
    (APP(APP(TOP, x), y), True, APP(TOP, y)),
    (BOT, False, BOT),
    (APP(BOT, x), True, BOT),
    (APP(APP(BOT, x), y), True, APP(BOT, y)),
    (I, False, I),
    (APP(I, x), True, x),
    (APP(APP(I, x), y), True, APP(x, y)),
    (APP(APP(I, x), APP(I, y)), True, APP(x, APP(I, y))),
    (APP(x, APP(I, y)), True, APP(x, y)),
    (K, False, K),
    (APP(K, x), False, APP(K, x)),
    (APP(APP(K, x), y), True, x),
    (APP(APP(APP(K, x), y), z), True, APP(x, z)),
    (B, False, B),
    (APP(B, x), False, APP(B, x)),
    (APP(APP(B, x), y), False, APP(APP(B, x), y)),
    (APP(APP(APP(B, x), y), z), True, APP(x, APP(y, z))),
    (C, False, C),
    (APP(C, x), False, APP(C, x)),
    (APP(APP(C, x), y), False, APP(APP(C, x), y)),
    (APP(APP(APP(C, x), y), z), True, APP(APP(x, z), y)),
    (S, False, S),
    (APP(S, x), False, APP(S, x)),
    (APP(APP(S, x), y), False, APP(APP(S, x), y)),
    (APP(APP(APP(S, x), y), z), True, APP(APP(x, z), APP(y, z))),
]


@for_each(BETA_STEP_EXAMPLES)
def test_try_beta_step(node, expected_result, expected_node):
    node = node.copy()
    assert try_beta_step(node) is expected_result
    assert node == expected_node


def test_try_beta_step_cyclic():
    actual = APP(APP(C, I), BOT)
    actual.set_arg(APP(I, actual))
    expected = APP(APP(C, I), BOT)
    expected.set_arg(expected)
    assert actual != expected
    actual = actual.copy()
    assert try_beta_step(actual)
    assert actual == expected


def const_stream(x):
    """Construct an infinite stream of xs."""
    result = APP(APP(C, APP(APP(C, I), x)), BOT)
    result.set_arg(result)
    return result


@for_each(BETA_STEP_EXAMPLES)
def test_try_beta_step_stream(x, expected_result, expected_x):
    actual = const_stream(x)
    expected = const_stream(expected_x)
    print('actual = {}'.format(print_to_depth(actual)))
    print('expected = {}'.format(print_to_depth(expected)))
    actual = actual.copy()
    assert try_beta_step(actual) is expected_result
    assert actual == expected


def test_equal_is_extensional():
    lhs = APP(x, APP(x, BOT))
    lhs.arg.set_arg(lhs)
    rhs = APP(x, BOT)
    rhs.set_arg(rhs)
    assert lhs == rhs
