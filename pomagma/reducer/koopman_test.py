from pomagma.reducer.koopman import (
    APP,
    ATOM,
    BOT,
    TOP,
    B,
    C,
    I,
    K,
    S,
    count_beta_steps,
    print_to_depth,
    try_beta_step,
)
from pomagma.util.testing import for_each, skip_param

f = ATOM("f")
x = ATOM("x")
y = ATOM("y")
z = ATOM("z")

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
    print(f"actual = {print_to_depth(actual)}")
    print(f"expected = {print_to_depth(expected)}")
    actual = actual.copy()
    assert try_beta_step(actual) is expected_result
    assert actual == expected


def test_equal_is_extensional():
    lhs = APP(x, APP(x, BOT))
    lhs.arg.set_arg(lhs)
    rhs = APP(x, BOT)
    rhs.set_arg(rhs)
    assert lhs == rhs


# ----------------------------------------------------------------------------
# Church numerals


def succ(x):
    return APP(APP(S, B), x)


def mult(x, y):
    return APP(x, y)


one = I
two = succ(one)
three = succ(two)
four = mult(two, two)
five = succ(four)
ten = mult(two, five)


def test_church_numeral_one():
    node = APP(APP(one, f), x)
    assert try_beta_step(node) is True
    assert node == APP(f, x)
    assert try_beta_step(node) is False


def test_church_numeral_two():
    node = APP(APP(two, f), x)
    assert try_beta_step(node) is True
    assert node == APP(APP(APP(B, f), APP(I, f)), x)
    assert try_beta_step(node) is True
    assert node == APP(f, APP(APP(I, f), x))
    assert try_beta_step(node) is True
    assert node == APP(f, APP(f, x))
    assert try_beta_step(node) is False


def test_church_numeral_three():
    node = APP(APP(three, f), x)
    assert try_beta_step(node) is True
    assert try_beta_step(node) is True
    assert try_beta_step(node) is True
    assert try_beta_step(node) is True
    assert try_beta_step(node) is True
    assert try_beta_step(node) is False
    assert node == APP(f, APP(f, APP(f, x)))


# Results:
@for_each(
    [
        1,  # Steps = 5.
        2,  # Steps = 14.
        3,  # Steps = 49.
        skip_param(4, reason="Steps = 131136"),  # Steps = 131136.
        skip_param(5, reason="Too slow"),
    ]
)
def test_tower_of_two(n):
    assert n >= 1
    node = two
    for _ in range(1, n):
        node = APP(node, two)
    node = APP(node, I)
    node = APP(node, x)
    node = node.copy()
    count = count_beta_steps(node)
    print(f"n = {n}, steps = {count}")
    assert node == x


def app(fun, *args):
    result = fun
    for arg in args:
        result = APP(result, arg)
    return result


"""
Table 1. The number of total interactions and beta-steps for various net-based
  implementations of reduction.
  From Mackie (2008) "An interaction-net implementation of closed reduction"

    Term           CVR             beta-optimal
    ----------------------------------------------
    2 I I          8(4)            12(4)
    2 2 I I        30(9)           40(9)
    2 2 2 I I      82(18)          93(16)
    2 2 2 2 I I    314(51)         356(27)
    2 2 2 2 2 I I  983346(131122)  1074037060(61)
    ----------------------------------------------
    3 2 I I        48(12)          47(12)
    4 2 I I        66(15)          63(15)
    5 2 I I        84(18)          79(18)
    10 2 I I       174(33)         159(33)
    3 2 2 I I      160(29)         157(21)
    4 2 2 I I      298(48)         330(26)
    5 2 2 I I      556(83)         847(31)
    10 2 2 I I     15526(2082)     531672(56)
    3 2 2 2 I I    3992(542)       34740(40)
    4 2 2 2 I I    983330(131121)  1074037034(60)
    ----------------------------------------------
    2 2 2 10 I I   1058(179)       10307(67)
    2 2 2 2 10 I I 4129050(655410) 1073933204(162)

Table 2. The number of total interactions and beta-steps for various net-based
  implementations of reduction.
  From Salikhmetov (2017) "Optimal reduction without oracle"

    Term           CVR             Salikhmetov  BOHM
    -----------------------------------------------------------
    2 2 2 10 I I   1058(179)       707(67)      10307(67)
    3 2 2 2 I I    3992(542)       1158(40)     34740(40)
    10 2 2 I I     15526(2082)     4282(56)     531672(56)
    4 2 2 2 I I    983330(131121)  262377(61)   1074037034(60)
    2 2 2 2 10 I I 4129050(655410) 2359780(198) 1073933204(162)
"""


@for_each(
    [
        # From table 1.
        app(two, I, I),
        app(two, two, I, I),
        app(two, two, two, I, I),
        app(two, two, two, two, I, I),
        skip_param(app(two, two, two, two, two, I, I), reason="Too slow"),
        # ---------------------------------------------------
        app(three, two, I, I),
        app(four, two, I, I),
        app(five, two, I, I),
        skip_param(app(ten, two, I, I), reason="Too slow"),
        skip_param(app(three, two, two, I, I), reason="Too slow"),
        skip_param(app(four, two, two, I, I), reason="Too slow"),
        skip_param(app(five, two, two, I, I), reason="Too slow"),
        skip_param(app(ten, two, two, I, I), reason="Too slow"),
        skip_param(app(three, two, two, two, I, I), reason="Too slow"),
        skip_param(app(four, two, two, two, I, I), reason="Too slow"),
        # From table 2.
        skip_param(app(two, two, two, ten, I, I), reason="Too slow"),
        skip_param(app(three, two, two, two, I, I), reason="Too slow"),
        skip_param(app(ten, two, two, I, I), reason="Too slow"),
        skip_param(app(four, two, two, two, I, I), reason="Too slow"),
        skip_param(app(two, two, two, two, ten, I, I), reason="Too slow"),
    ]
)
def test_benchmarks(node):
    count = count_beta_steps(node)
    print(f"steps = {count}")
