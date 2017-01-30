from pomagma.reducer.koopman import (APP, BOT, TOP, B, C, I, K, S,
                                     print_to_depth, try_beta_step)
from pomagma.util.testing import for_each

BETA_STEP_EXAMPLES = [
    (TOP, False, TOP),
    (BOT, False, BOT),
    (I, False, I),
    (K, False, K),
    (B, False, B),
    (C, False, C),
    (S, False, S),
    (APP(I, K), True, K),
    (APP(K, I), False, APP(K, I)),
    (APP(APP(K, B), C), True, B),
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
