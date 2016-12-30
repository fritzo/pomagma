import itertools

import hypothesis
import hypothesis.strategies as s
import pytest

from pomagma.reducer.bohm import (CB, CI, KI, TRY_DECIDE_LESS_STRONG, B, C, I,
                                  K, S, abstract, app, approximate,
                                  approximate_var, decrement_rank, dominates,
                                  false, ground, increment_rank, is_linear,
                                  is_normal, join, nominal_abstract,
                                  nominal_qabstract, polish_simplify,
                                  print_tiny, qabstract, reduce,
                                  sexpr_simplify, simplify, substitute, true,
                                  try_cast_bool, try_cast_code, try_cast_maybe,
                                  try_cast_unit, try_compute_step,
                                  try_decide_equal, try_decide_less,
                                  try_decide_less_weak, unabstract)
from pomagma.reducer.syntax import (ABS, APP, BOT, CODE, EQUAL, EVAL, IVAR,
                                    JOIN, LESS, NVAR, QAPP, QQUOTE, QUOTE, TOP,
                                    is_code, polish_print, quoted_vars,
                                    sexpr_parse, sexpr_print)
from pomagma.reducer.testing import iter_equations
from pomagma.util.testing import for_each, xfail_if_not_implemented

pretty = sexpr_print

i0 = IVAR(0)
i1 = IVAR(1)
i2 = IVAR(2)
i3 = IVAR(3)

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')

delta = ABS(APP(i0, i0))

ACTIVE_ATOMS = [EVAL, QAPP, QQUOTE, LESS, EQUAL]

s_atoms = s.one_of(
    s.sampled_from([TOP, BOT]),
    s.just(i0),
    s.just(i1),
    s.just(i2),
    s.just(i3),
    s.sampled_from([x, y, z]),
    s.sampled_from(ACTIVE_ATOMS),
)


def s_codes_extend(codes):
    return s.one_of(
        s.builds(app, codes, codes),
        s.builds(
            abstract,
            codes.filter(lambda c: i0 not in quoted_vars(c)),
        ),
        s.builds(join, codes, codes),
        s.builds(QUOTE, codes),
    )


s_codes = s.recursive(s_atoms, s_codes_extend, max_leaves=32)
s_quoted = s.builds(QUOTE, s_codes)


def test_constants():
    assert app(I, x) is x
    assert app(app(K, x), y) is x
    assert app(app(app(B, x), y), z) is APP(x, APP(y, z))
    assert app(app(app(C, x), y), z) is APP(APP(x, z), y)
    assert app(app(app(S, x), y), z) is APP(APP(x, z), APP(y, z))
    assert KI is app(K, I)
    assert CI is app(C, I)
    assert CB is app(C, B)


# ----------------------------------------------------------------------------
# Functional programming

INCREMENT_RANK_EXAMPLES = [
    (TOP, TOP),
    (BOT, BOT),
    (x, x),
    (y, y),
    (i0, i1),
    (i1, i2),
    (i2, i3),
    (ABS(i0), ABS(i0)),
    (ABS(i1), ABS(i2)),
    (ABS(i2), ABS(i3)),
    (ABS(ABS(i0)), ABS(ABS(i0))),
    (ABS(ABS(i1)), ABS(ABS(i1))),
    (ABS(ABS(i2)), ABS(ABS(i3))),
    (APP(i0, i1), APP(i1, i2)),
    (ABS(APP(i0, i0)), ABS(APP(i0, i0))),
    (ABS(APP(i1, i2)), ABS(APP(i2, i3))),
    (JOIN(i0, i1), JOIN(i1, i2)),
    (QUOTE(i0), QUOTE(i1)),
    (EVAL, EVAL),
    (QAPP, QAPP),
    (QQUOTE, QQUOTE),
    (LESS, LESS),
    (EQUAL, EQUAL),
]


@for_each(INCREMENT_RANK_EXAMPLES)
def test_increment_rank(code, expected):
    assert increment_rank(code) is expected


DECREMENT_RANK_EXAMPLES = [
    (TOP, TOP),
    (BOT, BOT),
    (x, x),
    (y, y),
    (i1, i0),
    (i2, i1),
    (i3, i2),
    (APP(i1, i2), APP(i0, i1)),
    (ABS(APP(i0, i0)), ABS(APP(i0, i0))),
    (ABS(APP(i2, i3)), ABS(APP(i1, i2))),
    (JOIN(i1, i2), JOIN(i0, i1)),
    (QUOTE(i1), QUOTE(i0)),
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
    assert decrement_rank(increment_rank(code)) is code


IS_LINEAR_EXAMPLES = [
    (TOP, True),
    (BOT, True),
    (x, True),
    (y, True),
    (i0, True),
    (i1, True),
    (APP(i0, i0), True),
    (APP(i0, i1), True),
    (APP(i1, i0), True),
    (APP(i1, i1), True),
    (ABS(APP(i0, i0)), False),
    (ABS(APP(i0, i1)), True),
    (ABS(APP(i1, i0)), True),
    (ABS(APP(i1, i1)), True),
    (ABS(JOIN(i0, APP(i0, x))), True),
    (ABS(JOIN(i0, APP(i0, i0))), False),
    (QUOTE(ABS(APP(i0, i0))), True),
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
    (i0, x, x),
    (i1, x, i0),
    (i2, x, i1),
    (APP(i0, i1), x, APP(x, i0)),
    (ABS(i0), x, ABS(i0)),
    (ABS(i1), x, ABS(x)),
    (ABS(i2), x, ABS(i1)),
    (JOIN(i0, i1), x, JOIN(i0, x)),
    (QUOTE(i0), x, QUOTE(x)),
    (QUOTE(i1), x, QUOTE(i0)),
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
    (TOP, i0, TOP),
    (BOT, TOP, BOT),
    (BOT, BOT, BOT),
    (BOT, x, BOT),
    (BOT, i0, BOT),
    (x, TOP, APP(x, TOP)),
    (x, BOT, APP(x, BOT)),
    (x, x, APP(x, x)),
    (x, i0, APP(x, i0)),
    (i0, TOP, APP(i0, TOP)),
    (i0, BOT, APP(i0, BOT)),
    (i0, x, APP(i0, x)),
    (i0, i0, APP(i0, i0)),
    (ABS(i1), TOP, i0),
    (ABS(i1), BOT, i0),
    (ABS(i1), x, i0),
    (ABS(i0), TOP, TOP),
    (ABS(i0), BOT, BOT),
    (ABS(i0), x, x),
    (ABS(APP(i0, y)), TOP, TOP),
    (ABS(APP(i0, y)), BOT, BOT),
    (ABS(APP(i0, y)), x, APP(x, y)),
    (ABS(APP(i0, i1)), x, APP(x, i0)),
    (JOIN(x, y), z, JOIN(APP(x, z), APP(y, z))),
    (JOIN(ABS(i0), x), TOP, TOP),
    (JOIN(ABS(i0), x), BOT, APP(x, BOT)),
    (QUOTE(TOP), x, APP(QUOTE(TOP), x)),
    (EVAL, TOP, TOP),
    (EVAL, BOT, BOT),
    (EVAL, QUOTE(x), x),
    (EVAL, QUOTE(i0), i0),
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
    (APP(LESS, BOT), i1, APP(APP(LESS, BOT), i1)),
    (APP(LESS, QUOTE(i0)), TOP, TOP),
    (APP(LESS, QUOTE(i0)), BOT, BOT),
    (APP(LESS, QUOTE(i0)), QUOTE(i1), false),
    (APP(LESS, QUOTE(i0)), QUOTE(i0), true),
    (APP(LESS, QUOTE(i0)), i1, APP(APP(LESS, QUOTE(i0)), i1)),
    (APP(LESS, i0), TOP, TOP),
    (APP(LESS, i0), BOT, APP(APP(LESS, i0), BOT)),
    (APP(LESS, i0), QUOTE(i1), APP(APP(LESS, i0), QUOTE(i1))),
    (APP(LESS, i0), i1, APP(APP(LESS, i0), i1)),
    (APP(EQUAL, TOP), TOP, TOP),
    (APP(EQUAL, TOP), BOT, TOP),
    (APP(EQUAL, TOP), QUOTE(i1), TOP),
    (APP(EQUAL, TOP), i1, TOP),
    (APP(EQUAL, BOT), TOP, TOP),
    (APP(EQUAL, BOT), BOT, BOT),
    (APP(EQUAL, BOT), QUOTE(i1), BOT),
    (APP(EQUAL, BOT), i1, APP(APP(EQUAL, BOT), i1)),
    (APP(EQUAL, QUOTE(i0)), TOP, TOP),
    (APP(EQUAL, QUOTE(i0)), BOT, BOT),
    (APP(EQUAL, QUOTE(i0)), QUOTE(i1), false),
    (APP(EQUAL, QUOTE(i0)), QUOTE(i0), true),
    (APP(EQUAL, QUOTE(i0)), i1, APP(APP(EQUAL, QUOTE(i0)), i1)),
    (APP(EQUAL, i0), TOP, TOP),
    (APP(EQUAL, i0), BOT, APP(APP(EQUAL, i0), BOT)),
    (APP(EQUAL, i0), QUOTE(i1), APP(APP(EQUAL, i0), QUOTE(i1))),
    (APP(EQUAL, i0), i1, APP(APP(EQUAL, i0), i1)),
]


@for_each(APP_EXAMPLES)
def test_app(fun, arg, expected):
    with xfail_if_not_implemented():
        assert pretty(app(fun, arg)) == pretty(expected)


ABSTRACT_EXAMPLES = [
    (TOP, TOP),
    (BOT, BOT),
    (x, ABS(x)),
    (i0, ABS(i0)),
    (i1, ABS(i1)),
    (ABS(i0), ABS(ABS(i0))),
    (APP(i0, x), ABS(APP(i0, x))),
    (APP(i0, i0), ABS(APP(i0, i0))),
    (APP(x, i0), x),
    (JOIN(i0, x), JOIN(ABS(i0), ABS(x))),
    (QUOTE(i1), ABS(QUOTE(i1))),
    (APP(QUOTE(i1), i0), QUOTE(i0)),
    (EVAL, ABS(EVAL)),
    (QAPP, ABS(QAPP)),
    (QQUOTE, ABS(QQUOTE)),
]


@for_each(ABSTRACT_EXAMPLES)
def test_abstract(code, expected):
    assert abstract(code) is expected


@hypothesis.given(s_codes)
def test_abstract_eta(code):
    assert abstract(app(increment_rank(code), i0)) is code


@hypothesis.given(s_codes)
@hypothesis.example(join(TOP, APP(QUOTE(i1), i0)))
def test_app_abstract(code):
    hypothesis.assume(i0 not in quoted_vars(code))
    assert app(increment_rank(abstract(code)), i0) is code


QABSTRACT_EXAMPLES = [
    (i0, EVAL),
    (i1, ABS(i1)),
]


@for_each(QABSTRACT_EXAMPLES)
def test_qabstract(code, expected):
    assert qabstract(code) is expected


@for_each([
    (x, x, ABS(i0)),
    (x, y, ABS(y)),
    (x, i0, ABS(i1)),
])
def test_nominal_abstract(var, body, expected):
    assert nominal_abstract(var, body) is expected


@for_each([
    (x, x, EVAL),
    (x, y, ABS(y)),
    (x, i0, ABS(i1)),
    (x, QUOTE(x), CODE),
    (x, QUOTE(APP(y, x)), APP(QAPP, QUOTE(y))),
])
def test_nominal_qabstract(var, body, expected):
    assert nominal_qabstract(var, body) is expected


# ----------------------------------------------------------------------------
# Scott ordering

APPROXIMATE_VAR_EXAMPLES = [
    (TOP, TOP, 0, [TOP]),
    (TOP, BOT, 0, [TOP]),
    (BOT, TOP, 0, [BOT]),
    (BOT, BOT, 0, [BOT]),
    (x, TOP, 0, [x]),
    (x, BOT, 0, [x]),
    (i0, TOP, 0, [i0, TOP]),
    (i0, BOT, 0, [i0, BOT]),
    # APP
    (
        APP(i0, i1),
        TOP,
        0,
        [
            APP(i0, i1),
            TOP,
        ],
    ),
    (
        APP(i0, i1),
        BOT,
        0,
        [
            APP(i0, i1),
            BOT,
        ],
    ),
    (
        APP(i1, i0),
        TOP,
        0,
        [
            APP(i1, i0),
            APP(i1, TOP),
        ],
    ),
    (
        APP(i1, i0),
        BOT,
        0,
        [
            APP(i1, i0),
            APP(i1, BOT),
        ],
    ),
    (
        APP(i0, i0),
        TOP,
        0,
        [
            APP(i0, i0),
            APP(i0, TOP),
            TOP,
        ],
    ),
    (
        APP(i0, i0),
        BOT,
        0,
        [
            APP(i0, i0),
            APP(i0, BOT),
            BOT,
        ],
    ),
    # JOIN
    (
        JOIN(i0, i1),
        TOP,
        0,
        [
            JOIN(i0, i1),
            TOP,
        ],
    ),
    (
        JOIN(i0, i1),
        BOT,
        0,
        [
            JOIN(i0, i1),
            i1,
        ],
    ),
    (
        JOIN(APP(x, i0), APP(y, i0)),
        TOP,
        0,
        [
            JOIN(APP(x, i0), APP(y, i0)),
            JOIN(APP(x, TOP), APP(y, i0)),
            JOIN(APP(x, i0), APP(y, TOP)),
            JOIN(APP(x, TOP), APP(y, TOP)),
        ],
    ),
    # QUOTE
    (
        QUOTE(i0),
        TOP,
        0,
        [QUOTE(i0)],
    )
]


@for_each(APPROXIMATE_VAR_EXAMPLES)
def test_approximate_var(code, direction, rank, expected):
    assert set(approximate_var(code, direction, rank)) == set(expected)


# TODO This is difficult to test, because the simplest argument that not
# is_cheap_to_copy is already very complex. We could mock, but that would
# pollute the memoized caches.
APPROXIMATE_EXAMPLES = [
    (i0, TOP, [i0]),
    (i0, BOT, [i0]),
    # TODO Add more examples.
]


@for_each(APPROXIMATE_EXAMPLES)
def test_approximate(code, direction, expected):
    assert set(approximate(code, direction)) == set(expected)


JOIN_EXAMPLES = [
    (TOP, TOP, TOP),
    (TOP, BOT, TOP),
    (TOP, x, TOP),
    (TOP, APP(QUOTE(i1), i0), TOP),
    (TOP, i0, TOP),
    (BOT, TOP, TOP),
    (BOT, BOT, BOT),
    (BOT, x, x),
    (BOT, i0, i0),
    (x, TOP, TOP),
    (x, BOT, x),
    (i0, TOP, TOP),
    (i0, BOT, i0),
    (i0, i0, i0),
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


@hypothesis.given(s_codes)
def test_join_top(code):
    assert join(code, TOP) is TOP
    assert join(TOP, code) is TOP


@hypothesis.given(s_codes)
def test_join_bot(code):
    assert join(code, BOT) is code
    assert join(BOT, code) is code


@hypothesis.given(s_codes, s_codes, s_codes)
def test_join_associative(x, y, z):
    assert join(join(x, y), z) is join(x, join(y, z))


@hypothesis.given(s_codes, s_codes)
def test_join_commutative(lhs, rhs):
    assert join(lhs, rhs) is join(rhs, lhs)


@hypothesis.given(s_codes)
def test_join_idempotent_1(code):
    assert join(code, code) is code


@hypothesis.given(s_codes, s_codes)
def test_join_idempotent_2(lhs, rhs):
    expected = join(lhs, rhs)
    assert join(lhs, expected) is expected
    assert join(rhs, expected) is expected


@hypothesis.given(s_codes)
def test_unabstract(code):
    assert abstract(unabstract(code)) is code


INCOMPARABLE_PAIRS = [
    (i0, i1),
    (i0, EVAL),
    (i0, QAPP),
    (i0, QQUOTE),
    (i0, LESS),
    (i0, EQUAL),
    (i0, QUOTE(TOP)),
    (QUOTE(TOP), QUOTE(BOT)),
    (i0, ABS(i0)),
    (i0, ABS(ABS(i0))),
    (i0, ABS(i1)),
    (i0, ABS(ABS(i1))),
    (ABS(i0), ABS(ABS(i0))),
    (ABS(i0), ABS(ABS(i1))),
    (APP(APP(i0, i1), i2), APP(APP(i0, TOP), BOT)),
    (APP(APP(i0, i1), i2), APP(APP(i0, BOT), TOP)),
    pytest.mark.xfail((ABS(i0), EVAL)),
]

INCOMPARABLE_CODES = [
    ABS(i0),
    ABS(APP(i0, i0)),
    ABS(APP(APP(i0, i0), APP(i0, i0))),
    ABS(ABS(i0)),
    ABS(ABS(i1)),
    ABS(ABS(APP(i0, i0))),
    ABS(ABS(APP(i0, i1))),
    ABS(ABS(APP(i1, i1))),
    # TODO Fix missed opportunity with unabstract(atom).
    # EVAL,
    # QAPP,
    # QQUOTE,
    # LESS,
    # EQUAL,
]

W = ABS(ABS(APP(APP(i1, i0), i0)))
delta_top = ABS(APP(i0, ABS(APP(i1, TOP))))
delta_bot = ABS(APP(i0, ABS(APP(i1, BOT))))

DOMINATING_PAIRS = [
    (BOT, TOP),
    (BOT, i0),
    (BOT, i1),
    (i0, TOP),
    (i1, TOP),
    (APP(APP(i0, BOT), i2), APP(APP(i0, i1), i2)),
    (APP(APP(i0, i1), BOT), APP(APP(i0, i1), i2)),
    (APP(APP(i0, i1), i2), APP(APP(i0, TOP), i2)),
    (APP(APP(i0, i1), i2), APP(APP(i0, i1), TOP)),
    (APP(APP(i0, BOT), i2), APP(APP(i0, i1), TOP)),
    (APP(APP(i0, i1), BOT), APP(APP(i0, TOP), i2)),
    (APP(APP(i0, i1), i2), APP(APP(i0, JOIN(i1, i2)), i2)),
    (APP(APP(i0, i1), i2), APP(APP(i0, i1), JOIN(i1, i2))),
    (APP(i0, i1), APP(i0, JOIN(i1, i2))),
    (APP(i0, i2), APP(i0, JOIN(i1, i2))),
    (APP(i0, JOIN(i1, i2)), APP(i0, TOP)),
    (ABS(APP(i1, BOT)), i0),
    (i0, ABS(APP(i1, TOP))),
    (APP(i0, i0), APP(i0, ABS(APP(i1, TOP)))),
    (delta_bot, delta),  # FIXME These are actually equal: delta delta = BOT.
    (delta, delta_top),
    # FIXME These are proven LESS and should be easy to prove NLESS.
    pytest.mark.xfail((APP(W, delta_bot), APP(W, delta))),
    pytest.mark.xfail((APP(W, delta), APP(W, delta_top))),
]


@for_each(INCOMPARABLE_PAIRS)
def test_try_decide_less_incomparable_pairs(lhs, rhs):
    assert try_decide_less_weak(lhs, rhs) is False
    assert try_decide_less_weak(rhs, lhs) is False


@for_each(itertools.combinations(INCOMPARABLE_CODES, 2))
def test_try_decide_less_incomparable_codes(lhs, rhs):
    assert try_decide_less_weak(lhs, rhs) is False
    assert try_decide_less_weak(rhs, lhs) is False


@for_each(DOMINATING_PAIRS)
def test_try_decide_less_dominating(lhs, rhs):
    assert try_decide_less_weak(lhs, rhs) is True
    assert try_decide_less_weak(rhs, lhs) is False


@hypothesis.given(s_codes)
def test_try_decide_less_reflexive(code):
    assert try_decide_less_weak(code, code) is True


@hypothesis.given(s_codes)
def test_try_decide_less_top(code):
    assert try_decide_less_weak(code, TOP) is True


@hypothesis.given(s_codes)
def test_try_decide_less_bot(code):
    assert try_decide_less_weak(BOT, code) is True


@hypothesis.given(s_codes, s_codes)
def test_try_decide_less_join(lhs, rhs):
    assert try_decide_less_weak(lhs, join(lhs, rhs)) is True
    assert try_decide_less_weak(rhs, join(lhs, rhs)) is True


@for_each(ACTIVE_ATOMS)
def test_try_decide_less_atom(atom):
    assert try_decide_less_weak(TOP, atom) is False
    assert try_decide_less_weak(atom, BOT) is False


@for_each(itertools.combinations(ACTIVE_ATOMS, 2))
def test_try_decide_less_atom_atom(lhs, rhs):
    assert try_decide_less_weak(lhs, rhs) is False


@hypothesis.given(s_codes, s_codes)
@hypothesis.settings(max_examples=1000)
def test_try_decide_less_weak(lhs, rhs):
    expected = try_decide_less_weak(lhs, rhs)
    hypothesis.assume(expected is not None)
    assert try_decide_less(lhs, rhs) is expected


@hypothesis.given(s_codes, s_codes)
def test_app_less(lhs, rhs):
    truth_value = try_decide_less(lhs, rhs)
    assert truth_value in (True, False, None)
    if truth_value is True:
        expected = true
    elif truth_value is False:
        expected = false
    else:
        expected = APP(APP(LESS, QUOTE(lhs)), QUOTE(rhs))
    assert app(app(LESS, QUOTE(lhs)), QUOTE(rhs)) is expected


@hypothesis.given(s_codes)
def test_try_decide_equal_reflexive(code):
    assert try_decide_equal(code, code) is True


@for_each(INCOMPARABLE_PAIRS)
def test_try_decide_equal_incomparable(lhs, rhs):
    assert try_decide_equal(lhs, rhs) is False
    assert try_decide_equal(rhs, lhs) is False


@hypothesis.given(s_codes, s_codes)
def test_app_equal(lhs, rhs):
    truth_value = try_decide_equal(lhs, rhs)
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
# Type casting

@for_each([
    (x, BOT, TOP),
    (i0, BOT, TOP),
    (ABS(i0), ABS(i0), ABS(i0)),
    (ABS(i1), BOT, TOP),
    (JOIN(x, I), I, TOP),
    (ABS(APP(i0, x)), ABS(APP(i0, BOT)), ABS(APP(i0, TOP))),
    (QUOTE(BOT), QUOTE(BOT), QUOTE(BOT)),
    (QUOTE(x), BOT, TOP),
])
def test_ground(code, expected_lb, expected_ub):
    lb, ub = ground(code)
    assert lb is expected_lb
    assert ub is expected_ub


@hypothesis.given(s_codes)
def test_ground_less(code):
    lb, ub = ground(code)
    assert try_decide_less(lb, ub) is True
    if TRY_DECIDE_LESS_STRONG:
        assert try_decide_less(lb, code) is True
        assert try_decide_less(code, ub) is True
    else:
        assert try_decide_less(lb, code) is not False
        assert try_decide_less(code, ub) is not False


F = KI
J = join(K, F)


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (I, I),
    (K, TOP),
    (F, TOP),
    (J, TOP),
    (app(app(B, K), app(CI, TOP)), TOP),
    (app(app(B, K), app(CI, BOT)), I),
    (x, None),
])
def test_try_cast_unit(x, expected):
    assert try_cast_unit(x) is expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (K, K),
    (F, F),
    (I, TOP),
    (J, TOP),
    (x, None),
])
def test_try_cast_bool(x, expected):
    assert try_cast_bool(x) is expected


none = K


def some(x):
    return app(K, app(CI, x))


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (none, none),
    (some(TOP), some(TOP)),
    (some(BOT), some(BOT)),
    (some(I), some(I)),
    (some(K), some(K)),
    (some(F), some(F)),
    (join(some(K), some(F)), some(J)),
    (app(app(J, none), some(BOT)), TOP),
    (I, TOP),
    (F, TOP),
    (J, TOP),
    (x, None),
])
def test_try_cast_maybe(x, expected):
    assert try_cast_maybe(x) is expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (QUOTE(x), QUOTE(x)),
    (app(QQUOTE, x), app(QQUOTE, x)),
    (app(app(QAPP, x), y), app(app(QAPP, x), y)),
    (x, None),
])
def test_try_cast_code(x, expected):
    assert try_cast_code(x) is expected


# ----------------------------------------------------------------------------
# Computation

COMPUTE_EXAMPLES = [
    (TOP, None),
    (BOT, None),
    (i0, None),
    (i1, None),
    (i2, None),
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


nonterminating_example_1 = (
    '(JOIN (ABS (0 0 (ABS (ABS (2 2 (ABS (ABS (ABS (0 (ABS (5 (3 0))) (ABS (2 '
    '(4 0))))))))))) (JOIN (ABS (ABS (0 (ABS 0) (ABS 0)))) (ABS (0 0 (ABS (ABS'
    '(2 2 (ABS (ABS (ABS (0 (ABS (5 (3 0))) (ABS (2 (4 0))))))))))))) (ABS (AB'
    'S (ABS (2 2) (JOIN (ABS (ABS (0 (ABS 0) (ABS 0)))) (ABS (0 0 (ABS (ABS (2'
    '2 (ABS (ABS (ABS (0 (ABS (5 (3 0))) (ABS (2 (4 0))))))))))))) (ABS (ABS ('
    'ABS (0 (ABS (5 (3 0))) (ABS (2 (4 0)))))))))) (ABS (ABS (ABS (2 2) (JOIN '
    '(ABS (ABS (0 (ABS 0) (ABS 0)))) (ABS (0 0 (ABS (ABS (2 2 (ABS (ABS (ABS ('
    '0 (ABS (5 (3 0))) (ABS (2 (4 0))))))))))))) (ABS (ABS (ABS (0 (ABS (5 (3 '
    '0))) (ABS (2 (4 0)))))))))) (ABS (ABS (ABS (2 2) (JOIN (ABS (ABS (0 (ABS '
    '0) (ABS 0)))) (ABS (0 0 (ABS (ABS (2 2 (ABS (ABS (ABS (0 (ABS (5 (3 0))) '
    '(ABS (2 (4 0))))))))))))) (ABS (ABS (ABS (0 (ABS (5 (3 0))) (ABS (2 (4 0)'
    '))))))))) (ABS (ABS (ABS (ABS (3 (1 (2 0))))))) (ABS 0)) (JOIN (ABS 0) (J'
    'OIN (ABS (0 (ABS (ABS (ABS (ABS (3 (1 (2 0))))))) (ABS 0))) (JOIN (ABS (A'
    'BS (ABS (ABS (ABS (ABS (4 (ABS (ABS (0 (ABS (ABS (ABS (ABS (9 3 (1 (2 0))'
    '))))) (ABS (2 (8 0)))))) (1 (2 0))))))))) (ABS (ABS (1 0 (1 0) (ABS (ABS '
    '(ABS (0 (ABS (5 4 (3 0))) (ABS (2 (ABS (1 1 (ABS (ABS (ABS (0 (ABS (5 (3 '
    '0))) (ABS (2 (4 0))))))))))))))))))))))'
)


@for_each([
    nonterminating_example_1,
])
def test_try_compute_step_terminates(code):
    code = sexpr_simplify(code)
    try_compute_step(code)


SIMPLIFY_EXAMPLES = [
    ('I', '(ABS 0)'),
    ('K', '(ABS (ABS 1))'),
    ('(I I)', '(ABS 0)'),
]


@for_each(SIMPLIFY_EXAMPLES)
def test_simplify(code, expected):
    code = sexpr_parse(code)
    expected = sexpr_parse(expected)
    assert simplify(code) is expected


@for_each(SIMPLIFY_EXAMPLES)
def test_reduce_simplifies(code, expected):
    code = sexpr_parse(code)
    expected = sexpr_parse(expected)
    budget = 10
    assert reduce(code, budget) is expected


@for_each([
    ('(ABS (0 0) (ABS (0 0)))', 0, '(ABS (0 0) (ABS (0 0)))'),
    ('(ABS (0 0) (ABS (0 0)))', 1, '(ABS (0 0) (ABS (0 0)))'),
])
def test_reduce(code, budget, expected):
    code = sexpr_parse(code)
    expected = sexpr_parse(expected)
    assert reduce(code, budget) is expected


@for_each(iter_equations('bohm'))
def test_reduce_equations(code, expected, message):
    with xfail_if_not_implemented():
        actual = reduce(code)
        expected = simplify(expected)
    assert actual == expected, message


# ----------------------------------------------------------------------------
# Eager parsing

PARSE_EXAMPLES = [
    ('I', '(ABS 0)'),
    ('K', '(ABS (ABS 1))'),
    ('B', '(ABS (ABS (ABS (2 (1 0)))))'),
    ('C', '(ABS (ABS (ABS (2 0 1))))'),
    ('S', '(ABS (ABS (ABS (2 0 (1 0)))))'),
    ('(I x)', 'x'),
    ('(K x)', '(ABS x)'),
    ('(K x y)', 'x'),
    ('(B x)', '(ABS (ABS (x (1 0))))'),
    ('(B x y)', '(ABS (x (y 0)))'),
    ('(B x y z)', '(x (y z))'),
    ('(C x)', '(ABS (ABS (x 0 1)))'),
    ('(C x y)', '(ABS (x 0 y))'),
    ('(C x y z)', '(x z y)'),
    ('(S x)', '(ABS (ABS (x 0 (1 0))))'),
    ('(S x y)', '(ABS (x 0 (y 0)))'),
    ('(S x y z)', '(x z (y z))'),
    ('(I I)', '(ABS 0)'),
    ('(I K)', '(ABS (ABS 1))'),
    ('(K I) ', '(ABS (ABS 0))'),
    ('(K I x y) ', 'y'),
    ('(I B)', '(ABS (ABS (ABS (2 (1 0)))))'),
    ('(B I)', '(ABS 0)'),
    ('(B I x)', 'x'),
    ('(B I x)', 'x'),
    ('(C B I)', '(ABS 0)'),
    ('(C B I x)', 'x'),
    ('(C (C x))', 'x'),
    ('(B C C)', '(ABS 0)'),
    ('(B C C x)', 'x'),
    ('(S K)', '(ABS (ABS 0))'),
    ('(S K I)', '(ABS 0)'),
    ('(S K K)', '(ABS 0)'),
    ('(S K x y)', 'y'),
    ('(FUN x (x y))', '(ABS (0 y))'),
    ('(FUN x (x 0))', '(ABS (0 1))'),
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


@for_each([
    ('0', '0'),
    ('(1 2)', '(12)'),
    ('(3 4 (5 6))', '(34(56))'),
    ('(ABS 0)', '^0'),
    ('(1 2 3)', '(123)'),
    ('(JOIN 1 (JOIN 2 3))', '[1|2|3]'),
])
def test_print_tiny(sexpr, expected):
    code = sexpr_simplify(sexpr)
    assert print_tiny(code) == expected
