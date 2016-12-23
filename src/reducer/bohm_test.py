from pomagma.reducer.bohm import (
    increment_rank, decrement_rank, is_const, is_linear, is_normal,
    substitute, app, abstract, join, occurs, approximate_var, approximate,
    true, false, try_prove_less, try_prove_nless, dominates,
    try_decide_less, try_decide_equal, try_compute_step,
    polish_simplify, sexpr_simplify,
)
from pomagma.reducer.code import (
    TOP, BOT, NVAR, IVAR, APP, ABS, JOIN,
    QUOTE, EVAL, QAPP, QQUOTE, LESS, EQUAL,
    polish_print, sexpr_parse, sexpr_print, is_code,
)
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis
import hypothesis.strategies as s
import itertools
import pytest

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')

delta = ABS(APP(IVAR(0), IVAR(0)))

s_atoms = s.one_of(
    s.sampled_from([TOP, BOT]),
    s.just(IVAR(0)),
    s.just(IVAR(1)),
    s.just(IVAR(2)),
    s.just(IVAR(3)),
    s.just(IVAR(4)),
    s.sampled_from([x, y, z]),
    s.sampled_from([EVAL, QAPP, QQUOTE, LESS, EQUAL]),
)


def s_codes_extend(codes):
    return s.one_of(
        s.builds(app, codes, codes),
        s.builds(abstract, codes),
        s.builds(join, codes, codes),
        s.builds(QUOTE, codes),
    )


s_codes = s.recursive(s_atoms, s_codes_extend, max_leaves=32)


# ----------------------------------------------------------------------------
# Functional programming

INCREMENT_RANK_EXAMPLES = [
    (TOP, 0, TOP),
    (BOT, 0, BOT),
    (x, 0, x),
    (y, 0, y),
    (IVAR(0), 0, IVAR(1)),
    (IVAR(1), 0, IVAR(2)),
    (IVAR(2), 0, IVAR(3)),
    (IVAR(0), 1, IVAR(0)),
    (IVAR(1), 1, IVAR(2)),
    (IVAR(2), 1, IVAR(3)),
    (IVAR(0), 2, IVAR(0)),
    (IVAR(1), 2, IVAR(1)),
    (IVAR(2), 2, IVAR(3)),
    (APP(IVAR(0), IVAR(1)), 0, APP(IVAR(1), IVAR(2))),
    (ABS(APP(IVAR(0), IVAR(0))), 0, ABS(APP(IVAR(0), IVAR(0)))),
    (ABS(APP(IVAR(1), IVAR(2))), 0, ABS(APP(IVAR(2), IVAR(3)))),
    (JOIN(IVAR(0), IVAR(1)), 0, JOIN(IVAR(1), IVAR(2))),
    (QUOTE(IVAR(0)), 0, QUOTE(IVAR(0))),
    (EVAL, 0, EVAL),
    (QAPP, 0, QAPP),
    (QQUOTE, 0, QQUOTE),
    (LESS, 0, LESS),
    (EQUAL, 0, EQUAL),
]


@for_each(INCREMENT_RANK_EXAMPLES)
def test_increment_rank(code, min_rank, expected):
    assert increment_rank(code, min_rank) is expected


DECREMENT_RANK_EXAMPLES = [
    (TOP, TOP),
    (BOT, BOT),
    (x, x),
    (y, y),
    (IVAR(1), IVAR(0)),
    (IVAR(2), IVAR(1)),
    (IVAR(3), IVAR(2)),
    (APP(IVAR(1), IVAR(2)), APP(IVAR(0), IVAR(1))),
    (ABS(APP(IVAR(0), IVAR(0))), ABS(APP(IVAR(0), IVAR(0)))),
    (ABS(APP(IVAR(2), IVAR(3))), ABS(APP(IVAR(1), IVAR(2)))),
    (JOIN(IVAR(1), IVAR(2)), JOIN(IVAR(0), IVAR(1))),
    (QUOTE(IVAR(0)), QUOTE(IVAR(0))),
    (EVAL, EVAL),
    (QAPP, QAPP),
    (QQUOTE, QQUOTE),
    (LESS, LESS),
    (EQUAL, EQUAL),
]


@for_each(DECREMENT_RANK_EXAMPLES)
def test_decrement_rank(code, expected):
    assert decrement_rank(code) is expected


@hypothesis.given(s_codes)
def test_decrement_increment_rank(code):
    assert decrement_rank(increment_rank(code, 0)) is code


IS_CONST_EXAMPLES = [
    (TOP, True),
    (BOT, True),
    (x, True),
    (y, True),
    (IVAR(0), False),
    (IVAR(1), True),
    (IVAR(2), True),
    (IVAR(3), True),
    (APP(IVAR(0), IVAR(0)), False),
    (APP(IVAR(0), IVAR(1)), False),
    (APP(IVAR(1), IVAR(0)), False),
    (APP(IVAR(1), IVAR(2)), True),
    (ABS(APP(IVAR(0), IVAR(0))), True),
    (ABS(APP(IVAR(0), IVAR(1))), False),
    (ABS(APP(IVAR(1), IVAR(0))), False),
    (JOIN(IVAR(0), IVAR(0)), False),
    (JOIN(IVAR(0), IVAR(1)), False),
    (JOIN(IVAR(1), IVAR(0)), False),
    (JOIN(IVAR(1), IVAR(2)), True),
    (QUOTE(IVAR(0)), True),
    (EVAL, True),
    (QAPP, True),
    (QQUOTE, True),
    (LESS, True),
    (EQUAL, True),
]


@for_each(IS_CONST_EXAMPLES)
def test_is_const(code, expected):
    assert is_const(code) is expected


IS_LINEAR_EXAMPLES = [
    (TOP, True),
    (BOT, True),
    (x, True),
    (y, True),
    (IVAR(0), True),
    (IVAR(1), True),
    (APP(IVAR(0), IVAR(0)), True),
    (APP(IVAR(0), IVAR(1)), True),
    (APP(IVAR(1), IVAR(0)), True),
    (APP(IVAR(1), IVAR(1)), True),
    (ABS(APP(IVAR(0), IVAR(0))), False),
    (ABS(APP(IVAR(0), IVAR(1))), True),
    (ABS(APP(IVAR(1), IVAR(0))), True),
    (ABS(APP(IVAR(1), IVAR(1))), True),
    (ABS(JOIN(IVAR(0), APP(IVAR(0), x))), True),
    (ABS(JOIN(IVAR(0), APP(IVAR(0), IVAR(0)))), False),
    (QUOTE(ABS(APP(IVAR(0), IVAR(0)))), True),
    (EVAL, True),
    (QAPP, True),
    (QQUOTE, True),
    (LESS, True),
    (EQUAL, True),
]


@for_each(IS_LINEAR_EXAMPLES)
def test_is_linear(code, expected):
    assert is_linear(code) is expected


SUBSTITUTE_EXAMPLES = [
    (TOP, BOT, TOP),
    (BOT, TOP, BOT),
    (x, TOP, x),
    (IVAR(0), x, x),
    (IVAR(1), x, IVAR(0)),
    (IVAR(2), x, IVAR(1)),
    (APP(IVAR(0), IVAR(1)), x, APP(x, IVAR(0))),
    (ABS(IVAR(0)), x, ABS(IVAR(0))),
    (ABS(IVAR(1)), x, ABS(x)),
    (ABS(IVAR(2)), x, ABS(IVAR(1))),
    (JOIN(IVAR(0), IVAR(1)), x, JOIN(IVAR(0), x)),
    (QUOTE(IVAR(0)), x, QUOTE(IVAR(0))),
    (QUOTE(IVAR(1)), x, QUOTE(IVAR(1))),
    (EVAL, x, EVAL),
    (QAPP, x, QAPP),
    (QQUOTE, x, QQUOTE),
    (LESS, x, LESS),
    (EQUAL, x, EQUAL),
]


@for_each(SUBSTITUTE_EXAMPLES)
def test_substitute(body, value, expected):
    assert substitute(body, value, 0, False) is expected


APP_EXAMPLES = [
    (TOP, TOP, TOP),
    (TOP, BOT, TOP),
    (TOP, x, TOP),
    (BOT, TOP, BOT),
    (BOT, BOT, BOT),
    (BOT, x, BOT),
    (x, TOP, APP(x, TOP)),
    (x, BOT, APP(x, BOT)),
    (x, x, APP(x, x)),
    (IVAR(0), TOP, APP(IVAR(0), TOP)),
    (IVAR(0), BOT, APP(IVAR(0), BOT)),
    (IVAR(0), x, APP(IVAR(0), x)),
    (ABS(IVAR(1)), TOP, IVAR(0)),
    (ABS(IVAR(1)), BOT, IVAR(0)),
    (ABS(IVAR(1)), x, IVAR(0)),
    (ABS(IVAR(0)), TOP, TOP),
    (ABS(IVAR(0)), BOT, BOT),
    (ABS(IVAR(0)), x, x),
    (ABS(APP(IVAR(0), y)), TOP, TOP),
    (ABS(APP(IVAR(0), y)), BOT, BOT),
    (ABS(APP(IVAR(0), y)), x, APP(x, y)),
    (ABS(APP(IVAR(0), IVAR(1))), x, APP(x, IVAR(0))),
    (JOIN(x, y), z, JOIN(APP(x, z), APP(y, z))),
    pytest.mark.xfail((JOIN(ABS(IVAR(0)), x), TOP, TOP)),
    (JOIN(ABS(IVAR(0)), x), BOT, APP(x, BOT)),
    (QUOTE(TOP), x, APP(QUOTE(TOP), x)),
    (EVAL, TOP, TOP),
    (EVAL, BOT, BOT),
    (EVAL, QUOTE(x), x),
    (EVAL, x, APP(EVAL, x)),
    (QAPP, TOP, TOP),
    (QAPP, BOT, APP(QAPP, BOT)),
    (QAPP, QUOTE(x), APP(QAPP, QUOTE(x))),
    (QAPP, x, APP(QAPP, x)),
    (APP(QAPP, TOP), TOP, TOP),
    (APP(QAPP, TOP), BOT, TOP),
    (APP(QAPP, TOP), QUOTE(y), TOP),
    (APP(QAPP, TOP), y, TOP),
    (APP(QAPP, BOT), TOP, TOP),
    (APP(QAPP, BOT), BOT, BOT),
    (APP(QAPP, BOT), QUOTE(y), BOT),
    (APP(QAPP, BOT), y, APP(APP(QAPP, BOT), y)),
    (APP(QAPP, QUOTE(x)), TOP, TOP),
    (APP(QAPP, QUOTE(x)), BOT, BOT),
    (APP(QAPP, QUOTE(x)), QUOTE(y), QUOTE(APP(x, y))),
    (APP(QAPP, QUOTE(x)), y, APP(APP(QAPP, QUOTE(x)), y)),
    (APP(QAPP, x), TOP, TOP),
    (APP(QAPP, x), BOT, APP(APP(QAPP, x), BOT)),
    (APP(QAPP, x), QUOTE(y), APP(APP(QAPP, x), QUOTE(y))),
    (APP(QAPP, x), y, APP(APP(QAPP, x), y)),
    (QQUOTE, TOP, TOP),
    (QQUOTE, BOT, BOT),
    (QQUOTE, QUOTE(x), QUOTE(QUOTE(x))),
    (QQUOTE, x, APP(QQUOTE, x)),
    (APP(LESS, TOP), TOP, TOP),
    (APP(LESS, TOP), BOT, TOP),
    (APP(LESS, TOP), QUOTE(y), TOP),
    (APP(LESS, TOP), y, TOP),
    (APP(LESS, BOT), TOP, TOP),
    (APP(LESS, BOT), BOT, BOT),
    (APP(LESS, BOT), QUOTE(y), BOT),
    (APP(LESS, BOT), y, APP(APP(LESS, BOT), y)),
    (APP(LESS, QUOTE(x)), TOP, TOP),
    (APP(LESS, QUOTE(x)), BOT, BOT),
    (APP(LESS, QUOTE(x)), QUOTE(y), false),
    (APP(LESS, QUOTE(x)), QUOTE(x), true),
    (APP(LESS, QUOTE(x)), y, APP(APP(LESS, QUOTE(x)), y)),
    (APP(LESS, x), TOP, TOP),
    (APP(LESS, x), BOT, APP(APP(LESS, x), BOT)),
    (APP(LESS, x), QUOTE(y), APP(APP(LESS, x), QUOTE(y))),
    (APP(LESS, x), y, APP(APP(LESS, x), y)),
    (APP(EQUAL, TOP), TOP, TOP),
    (APP(EQUAL, TOP), BOT, TOP),
    (APP(EQUAL, TOP), QUOTE(y), TOP),
    (APP(EQUAL, TOP), y, TOP),
    (APP(EQUAL, BOT), TOP, TOP),
    (APP(EQUAL, BOT), BOT, BOT),
    (APP(EQUAL, BOT), QUOTE(y), BOT),
    (APP(EQUAL, BOT), y, APP(APP(EQUAL, BOT), y)),
    (APP(EQUAL, QUOTE(x)), TOP, TOP),
    (APP(EQUAL, QUOTE(x)), BOT, BOT),
    (APP(EQUAL, QUOTE(x)), QUOTE(y), false),
    (APP(EQUAL, QUOTE(x)), QUOTE(x), true),
    (APP(EQUAL, QUOTE(x)), y, APP(APP(EQUAL, QUOTE(x)), y)),
    (APP(EQUAL, x), TOP, TOP),
    (APP(EQUAL, x), BOT, APP(APP(EQUAL, x), BOT)),
    (APP(EQUAL, x), QUOTE(y), APP(APP(EQUAL, x), QUOTE(y))),
    (APP(EQUAL, x), y, APP(APP(EQUAL, x), y)),
]


@for_each(APP_EXAMPLES)
def test_app(fun, arg, expected):
    with xfail_if_not_implemented():
        assert app(fun, arg) is expected


ABSTRACT_EXAMPLES = [
    (TOP, TOP),
    (BOT, BOT),
    (x, ABS(x)),
    (IVAR(0), ABS(IVAR(0))),
    (IVAR(1), ABS(IVAR(1))),
    (ABS(IVAR(0)), ABS(ABS(IVAR(0)))),
    (APP(IVAR(0), x), ABS(APP(IVAR(0), x))),
    (APP(IVAR(0), IVAR(0)), ABS(APP(IVAR(0), IVAR(0)))),
    (APP(x, IVAR(0)), x),
    (JOIN(IVAR(0), x), JOIN(ABS(IVAR(0)), ABS(x))),
    (QUOTE(IVAR(0)), ABS(QUOTE(IVAR(0)))),
    (APP(QUOTE(IVAR(0)), IVAR(0)), QUOTE(IVAR(0))),
    (EVAL, ABS(EVAL)),
    (QAPP, ABS(QAPP)),
    (QQUOTE, ABS(QQUOTE)),
]


@for_each(ABSTRACT_EXAMPLES)
def test_abstract(code, expected):
    assert abstract(code) is expected


@pytest.mark.xfail(reason='join(-,-) does not handle ABS(-)')
@hypothesis.given(s_codes)
@hypothesis.example(join(TOP, ABS(IVAR(0))))
def test_abstract_eta(code):
    hypothesis.assume(is_const(code))
    assert abstract(app(code, IVAR(0))) is decrement_rank(code)


# ----------------------------------------------------------------------------
# Scott ordering

OCCURS_EXAMPLES = [
    (TOP, 0, False),
    (TOP, 1, False),
    (BOT, 0, False),
    (BOT, 1, False),
    (x, 0, False),
    (x, 1, False),
    (y, 0, False),
    (y, 1, False),
    (IVAR(0), 0, True),
    (IVAR(0), 1, False),
    (IVAR(1), 0, False),
    (IVAR(1), 1, True),
    # TODO Add more examples.
    (ABS(IVAR(0)), 0, False),
    (ABS(IVAR(1)), 0, True),
    (ABS(IVAR(2)), 0, False),
    (EVAL, 0, False),
    (QAPP, 0, False),
    (QQUOTE, 0, False),
]


@for_each(OCCURS_EXAMPLES)
def test_occurs(code, rank, expected):
    assert occurs(code, rank) is expected


APPROXIMATE_VAR_EXAMPLES = [
    (TOP, TOP, 0, [TOP]),
    (TOP, BOT, 0, [TOP]),
    (BOT, TOP, 0, [BOT]),
    (BOT, BOT, 0, [BOT]),
    (x, TOP, 0, [x]),
    (x, BOT, 0, [x]),
    (IVAR(0), TOP, 0, [IVAR(0), TOP]),
    (IVAR(0), BOT, 0, [IVAR(0), BOT]),
    # APP
    (
        APP(IVAR(0), IVAR(1)),
        TOP,
        0,
        [
            APP(IVAR(0), IVAR(1)),
            TOP,
        ],
    ),
    (
        APP(IVAR(0), IVAR(1)),
        BOT,
        0,
        [
            APP(IVAR(0), IVAR(1)),
            BOT,
        ],
    ),
    (
        APP(IVAR(1), IVAR(0)),
        TOP,
        0,
        [
            APP(IVAR(1), IVAR(0)),
            APP(IVAR(1), TOP),
        ],
    ),
    (
        APP(IVAR(1), IVAR(0)),
        BOT,
        0,
        [
            APP(IVAR(1), IVAR(0)),
            APP(IVAR(1), BOT),
        ],
    ),
    (
        APP(IVAR(0), IVAR(0)),
        TOP,
        0,
        [
            APP(IVAR(0), IVAR(0)),
            APP(IVAR(0), TOP),
            TOP,
        ],
    ),
    (
        APP(IVAR(0), IVAR(0)),
        BOT,
        0,
        [
            APP(IVAR(0), IVAR(0)),
            APP(IVAR(0), BOT),
            BOT,
        ],
    ),
    # JOIN
    (
        JOIN(IVAR(0), IVAR(1)),
        TOP,
        0,
        [
            JOIN(IVAR(0), IVAR(1)),
            TOP,
        ],
    ),
    (
        JOIN(IVAR(0), IVAR(1)),
        BOT,
        0,
        [
            JOIN(IVAR(0), IVAR(1)),
            IVAR(1),
        ],
    ),
    (
        JOIN(APP(x, IVAR(0)), APP(y, IVAR(0))),
        TOP,
        0,
        [
            JOIN(APP(x, IVAR(0)), APP(y, IVAR(0))),
            JOIN(APP(x, TOP), APP(y, IVAR(0))),
            JOIN(APP(x, IVAR(0)), APP(y, TOP)),
            JOIN(APP(x, TOP), APP(y, TOP)),
        ],
    ),
    # QUOTE
    (
        QUOTE(IVAR(0)),
        TOP,
        0,
        [QUOTE(IVAR(0))],
    )
]


@for_each(APPROXIMATE_VAR_EXAMPLES)
def test_approximate_var(code, direction, rank, expected):
    assert set(approximate_var(code, direction, rank)) == set(expected)


# TODO This is difficult to test, because the simplest argument that not
# is_cheap_to_copy is already very complex. We could mock, but that would
# pollute the memoized caches.
APPROXIMATE_EXAMPLES = [
    (IVAR(0), TOP, [IVAR(0)]),
    (IVAR(0), BOT, [IVAR(0)]),
    # TODO Add more examples.
]


@for_each(APPROXIMATE_EXAMPLES)
def test_approximate(code, direction, expected):
    assert set(approximate(code, direction)) == set(expected)


JOIN_EXAMPLES = [
    (TOP, TOP, TOP),
    (TOP, BOT, TOP),
    (TOP, x, TOP),
    (TOP, IVAR(0), TOP),
    (BOT, TOP, TOP),
    (BOT, BOT, BOT),
    (BOT, x, x),
    (BOT, IVAR(0), IVAR(0)),
    (x, TOP, TOP),
    (x, BOT, x),
    (IVAR(0), TOP, TOP),
    (IVAR(0), BOT, IVAR(0)),
    (IVAR(0), IVAR(0), IVAR(0)),
    (x, y, JOIN(x, y)),
    (JOIN(x, y), x, JOIN(x, y)),
    (JOIN(x, y), y, JOIN(x, y)),
    (JOIN(x, y), z, JOIN(x, JOIN(y, z))),
    (JOIN(x, z), y, JOIN(x, JOIN(y, z))),
    (JOIN(y, z), x, JOIN(x, JOIN(y, z))),
    (JOIN(x, z), JOIN(x, y), JOIN(x, JOIN(y, z))),
    (QUOTE(BOT), QUOTE(TOP), JOIN(QUOTE(BOT), QUOTE(TOP))),
]


@for_each(JOIN_EXAMPLES)
def test_join(lhs, rhs, expected):
    assert join(lhs, rhs) is expected


TRY_DECIDE_LESS_EXAMPLES = [
    (TOP, TOP, True),
    (TOP, BOT, False),
    (BOT, TOP, True),
    (BOT, BOT, True),
    (IVAR(0), IVAR(0), True),
    (IVAR(0), TOP, True),
    (IVAR(0), BOT, False),
    (TOP, IVAR(0), False),
    (BOT, IVAR(0), True),
    (IVAR(0), IVAR(1), False),
    (IVAR(1), IVAR(0), False),
    # TODO Add more examples.
]


@for_each(TRY_DECIDE_LESS_EXAMPLES)
def test_try_decide_less(lhs, rhs, expected):
    assert try_decide_less(lhs, rhs) is expected


@for_each(TRY_DECIDE_LESS_EXAMPLES)
def test_try_prove_less(lhs, rhs, truth_value):
    assert truth_value in (True, False, None)
    if truth_value is True:
        expected = True
    else:
        expected = False
    assert try_prove_less(lhs, rhs) is expected


@for_each(TRY_DECIDE_LESS_EXAMPLES)
def test_try_prove_nless(lhs, rhs, truth_value):
    assert truth_value in (True, False, None)
    if truth_value is False:
        expected = True
    else:
        expected = False
    assert try_prove_nless(lhs, rhs) is expected


@for_each(TRY_DECIDE_LESS_EXAMPLES)
def test_app_less(lhs, rhs, truth_value):
    assert truth_value in (True, False, None)
    if truth_value is True:
        expected = true
    elif truth_value is False:
        expected = false
    else:
        expected = APP(APP(LESS, QUOTE(lhs)), QUOTE(rhs))
    assert app(app(LESS, QUOTE(lhs)), QUOTE(rhs)) is expected


TRY_DECIDE_EQUAL_EXAMPLES = [
    (TOP, TOP, True),
    (BOT, BOT, True),
    (IVAR(0), IVAR(0), True),
    (IVAR(1), IVAR(1), True),
    (TOP, BOT, False),
    (BOT, TOP, False),
    (IVAR(0), TOP, False),
    (IVAR(0), BOT, False),
    (TOP, IVAR(0), False),
    (BOT, IVAR(0), False),
    (IVAR(0), IVAR(1), False),
    (IVAR(1), IVAR(0), False),
    # TODO Add more examples.
]


@for_each(TRY_DECIDE_EQUAL_EXAMPLES)
def test_try_decide_equal(lhs, rhs, expected):
    assert try_decide_equal(lhs, rhs) is expected


@for_each(TRY_DECIDE_EQUAL_EXAMPLES)
def test_app_equal(lhs, rhs, truth_value):
    assert truth_value in (True, False, None)
    if truth_value is True:
        expected = true
    elif truth_value is False:
        expected = false
    else:
        expected = APP(APP(EQUAL, QUOTE(lhs)), QUOTE(rhs))
    assert app(app(EQUAL, QUOTE(lhs)), QUOTE(rhs)) is expected


@hypothesis.given(s_codes)
def test_dominates_irreflexive(code):
    assert not dominates(code, code)


@hypothesis.given(s_codes, s_codes, s_codes)
def test_dominates_transitive(x, y, z):
    for x, y, z in itertools.permutations([x, y, z]):
        if dominates(x, y) and dominates(y, z):
            assert dominates(x, z)


# ----------------------------------------------------------------------------
# Computation

COMPUTE_EXAMPLES = [
    (TOP, None),
    (BOT, None),
    (IVAR(0), None),
    (IVAR(1), None),
    (IVAR(2), None),
    (delta, None),
    (APP(delta, delta), APP(delta, delta)),
    (APP(delta, APP(x, delta)), APP(APP(x, delta), APP(x, delta))),
    (EVAL, None),
    (QAPP, None),
    (QQUOTE, None),
    (LESS, None),
    (EQUAL, None),
]


@for_each(COMPUTE_EXAMPLES)
def test_is_normal(code, expected_try_compute_step):
    expected = (expected_try_compute_step is None)
    assert is_normal(code) is expected


@hypothesis.given(s_codes)
def test_linear_is_normal(code):
    hypothesis.assume(is_linear(code))
    assert is_normal(code)


@for_each(COMPUTE_EXAMPLES)
def test_try_compute_step(code, expected):
    with xfail_if_not_implemented():
        assert try_compute_step(code) is expected


@hypothesis.given(s_codes)
@hypothesis.settings(max_examples=1000)
def test_try_compute_step_runs(code):
    for step in xrange(5):
        with xfail_if_not_implemented():
            result = try_compute_step(code)
        if is_normal(code):
            assert result is None
            return
        else:
            assert is_code(result)


# ----------------------------------------------------------------------------
# Eager parsing

PARSE_EXAMPLES = [
    ('I', '(ABS (IVAR 0))'),
    ('K', '(ABS (ABS (IVAR 1)))'),
    ('B', '(ABS (ABS (ABS (IVAR 2 (IVAR 1 (IVAR 0))))))'),
    ('C', '(ABS (ABS (ABS (IVAR 2 (IVAR 0) (IVAR 1)))))'),
    ('S', '(ABS (ABS (ABS (IVAR 2 (IVAR 0) (IVAR 1 (IVAR 0))))))'),
    ('(I x)', 'x'),
    ('(K x)', '(ABS x)'),
    ('(K x y)', 'x'),
    ('(B x)', '(ABS (ABS (x (IVAR 1 (IVAR 0)))))'),
    ('(B x y)', '(ABS (x (y (IVAR 0))))'),
    ('(B x y z)', '(x (y z))'),
    ('(C x)', '(ABS (ABS (x (IVAR 0) (IVAR 1))))'),
    ('(C x y)', '(ABS (x (IVAR 0) y))'),
    ('(C x y z)', '(x z y)'),
    ('(S x)', '(ABS (ABS (x (IVAR 0) (IVAR 1 (IVAR 0)))))'),
    ('(S x y)', '(ABS (x (IVAR 0) (y (IVAR 0))))'),
    ('(S x y z)', '(x z (y z))'),
    ('(I I)', '(ABS (IVAR 0))'),
    ('(I K)', '(ABS (ABS (IVAR 1)))'),
    ('(K I) ', '(ABS (ABS (IVAR 0)))'),
    ('(K I x y) ', 'y'),
    ('(I B)', '(ABS (ABS (ABS (IVAR 2 (IVAR 1 (IVAR 0))))))'),
    ('(B I)', '(ABS (IVAR 0))'),
    ('(B I x)', 'x'),
    ('(B I x)', 'x'),
    ('(C B I)', '(ABS (IVAR 0))'),
    ('(C B I x)', 'x'),
    ('(C (C x))', 'x'),
    ('(B C C)', '(ABS (IVAR 0))'),
    ('(B C C x)', 'x'),
    ('(S K)', '(ABS (ABS (IVAR 0)))'),
    ('(S K I)', '(ABS (IVAR 0))'),
    ('(S K K)', '(ABS (IVAR 0))'),
    ('(S K x y)', 'y'),
]


@for_each(PARSE_EXAMPLES)
def test_polish_simplify(sexpr, expected):
    polish = polish_print(sexpr_parse(sexpr))
    assert polish_simplify(polish) is sexpr_parse(expected)


@for_each(PARSE_EXAMPLES)
def test_sexpr_simplify(sexpr, expected):
    assert sexpr_simplify(sexpr) is sexpr_parse(expected)


@hypothesis.given(s_codes)
def test_sexpr_print_simplify(code):
    sexpr = sexpr_print(code)
    assert sexpr_simplify(sexpr) is code
