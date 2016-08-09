from pomagma.reducer import continuation
from pomagma.reducer import lib
from pomagma.reducer.code import APP, VAR, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import EVAL, QQUOTE, EQUAL, LESS
from pomagma.reducer.sugar import app, join, quote, qapp
from pomagma.reducer.testing import iter_equations, s_codes, s_quoted
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis
import pytest

BUDGET = 10000

w = VAR('w')
x = VAR('x')
y = VAR('y')
z = VAR('z')
F = app(K, I)


@for_each([
    (S, None, None, 1 + 0 + 0),
    (x, None, None, 2 + 0 + 0),
    (S, None, (x, None), 1 + 0 + 3),
    (S, None, (y, (x, None)), 1 + 0 + 6),
    (S, (I, None), None, 1 + 2 + 0),
    (S, (I, None), (x, None), 1 + 2 + 3),
    (S, (I, None), (y, (x, None)), 1 + 2 + 6),
    (S, (x, None), None, 1 + 3 + 0),
    (S, (x, None), (x, None), 1 + 3 + 3),
    (S, (x, None), (y, (x, None)), 1 + 3 + 6),
    (S, (x, (I, None)), None, 1 + 5 + 0),
    (S, (x, (I, None)), (x, None), 1 + 5 + 3),
    (S, (x, (I, None)), (y, (x, None)), 1 + 5 + 6),
])
def test_cont_complexity(code, stack, bound, expected):
    cont = continuation.make_cont(code, stack, bound)
    assert continuation.cont_complexity(cont) == expected


def box(item):
    return app(C, I, item)


def enum(items):
    return join(*map(box, items))


# TODO migrate these to testdata/*.sexpr
REDUCE_EXAMPLES = [
    (x, x),
    (app(x, y), app(x, y)),
    (app(x, I), app(x, I)),
    (TOP, TOP),
    (app(TOP, x), TOP),
    (app(TOP, x, y), TOP),
    (BOT, BOT),
    (app(BOT, x), BOT),
    (app(BOT, x, y), BOT),
    (I, I),
    (app(I, x), x),
    pytest.mark.xfail((app(I, K), K)),
    pytest.mark.xfail((K, K)),
    (app(K, x), app(K, x)),
    (app(K, x, y), x),
    (app(K, x, y, z), app(x, z)),
    pytest.mark.xfail((B, B)),
    pytest.mark.xfail((app(B, x), app(B, x))),
    (app(B, x, y), app(B, x, y)),
    (app(B, x, y, z), app(x, app(y, z))),
    (app(B, x, y, z, w), app(x, app(y, z), w)),
    pytest.mark.xfail((C, C)),
    pytest.mark.xfail((app(C, x), app(C, x))),
    (app(C, x, y), app(C, x, y)),
    (app(C, x, y, z), app(x, z, y)),
    (app(C, x, y, z, w), app(x, z, y, w)),
    pytest.mark.xfail((S, S)),
    pytest.mark.xfail((app(S, x), app(S, x))),
    (app(S, x, y), app(S, x, y)),
    (app(S, x, y, z), app(x, z, app(y, z))),
    (app(S, x, y, z, w), app(x, z, app(y, z), w)),
    pytest.mark.xfail((J, J)),
    (app(J, x), app(J, x)),
    (join(x, y), join(x, y)),
    (join(x, x), x),
    (join(BOT, x), x),
    (join(TOP, x), TOP),
    pytest.mark.xfail((join(K, APP(K, I)), J)),
    pytest.mark.xfail((join(APP(K, I), K), J)),
    pytest.mark.xfail((join(J, K), J)),
    pytest.mark.xfail((join(K, J), J)),
    pytest.mark.xfail((join(J, APP(K, I)), J)),
    pytest.mark.xfail((join(APP(K, I), J), J)),
    pytest.mark.xfail((app(C, J), J)),
    (app(S, J, I), I),
    (app(join(x, y), z), join(app(x, z), app(y, z))),
    (app(join(I, app(K, I)), I), I),
    pytest.mark.xfail((app(join(I, app(K, I)), K), join(I, K))),
    (enum([I]), enum([I])),
    (enum([I, I]), enum([I])),
    (enum([I, BOT]), enum([I])),
    (enum([I, TOP]), enum([TOP])),
    (enum([BOT, I, TOP]), enum([TOP])),
    pytest.mark.xfail((enum([K, F]), enum([K, F]))),
    pytest.mark.xfail((enum([BOT, K, F]), enum([K, F]))),
    pytest.mark.xfail((enum([K, F, J]), enum([J]))),
    (enum([K, F, TOP]), enum([TOP])),
    (enum([BOT, box(BOT)]), enum([box(BOT)])),
    (enum([BOT, box(BOT), box(box(BOT))]), enum([box(box(BOT))])),
    (enum([BOT, box(BOT), box(box(BOT)), box(TOP)]), enum([box(TOP)])),
    pytest.mark.xfail((app(lib.list_map, I, lib.nil), lib.nil)),
    pytest.mark.xfail((lib.list_map(I, lib.nil), lib.nil)),
    pytest.mark.xfail(
        (lib.list_map(I, lib.cons(x, lib.nil)), lib.cons(x, lib.nil))
    ),
    (quote(x), quote(x)),
    (quote(app(I, x)), quote(x)),
    (app(EVAL, x), app(EVAL, x)),
    (app(EVAL, TOP), TOP),
    (app(EVAL, BOT), BOT),
    (app(EVAL, quote(I), x), x),
    (quote(app(EVAL, quote(app(K, I, I)))), quote(I)),
    (app(S, K, K, quote(app(EVAL, quote(app(K, I, I))))), quote(I)),
    (app(QQUOTE, x), app(QQUOTE, x)),
    (app(QQUOTE, quote(x)), quote(quote(x))),
    (app(QQUOTE, TOP), TOP),
    (app(QQUOTE, BOT), BOT),
    (qapp(x, y), qapp(x, y)),
    (qapp(quote(x), y), qapp(quote(x), y)),
    (qapp(x, quote(y)), qapp(x, quote(y))),
    (qapp(quote(x), quote(y)), quote(app(x, y))),
    (qapp(quote(S), quote(K), quote(K)), quote(I)),
    (qapp(quote(S), app(I, quote(K)), app(EVAL, quote(quote(K)))), quote(I)),
    (qapp(quote(lib.list_map), quote(I), quote(lib.nil)), quote(lib.nil)),
    (app(EQUAL, x, y), app(EQUAL, x, y)),
    (app(EQUAL, x, quote(y)), app(EQUAL, x, quote(y))),
    (app(EQUAL, quote(x), y), app(EQUAL, quote(x), y)),
    (app(EQUAL, quote(x), quote(y)), app(EQUAL, quote(x), quote(y))),
    (app(EQUAL, quote(x), quote(x)), lib.true),
    (app(EQUAL, quote(I), quote(K)), lib.false),
    (app(EQUAL, TOP, x), TOP),
    (app(EQUAL, x, TOP), TOP),
    (app(EQUAL, BOT, x), app(EQUAL, BOT, x)),
    (app(EQUAL, x, BOT), app(EQUAL, x, BOT)),
    (app(EQUAL, BOT, quote(x)), BOT),
    (app(EQUAL, quote(x), BOT), BOT),
    (app(LESS, x, y), app(LESS, x, y)),
    (app(LESS, x, quote(y)), app(LESS, x, quote(y))),
    (app(LESS, quote(x), y), app(LESS, quote(x), y)),
    (app(LESS, quote(x), quote(y)), app(LESS, quote(x), quote(y))),
    (app(LESS, quote(x), quote(x)), lib.true),
    (app(LESS, quote(BOT), quote(x)), lib.true),
    (app(LESS, quote(x), quote(TOP)), lib.true),
    (app(LESS, quote(TOP), quote(BOT)), lib.false),
    (app(LESS, TOP, x), TOP),
    (app(LESS, x, TOP), TOP),
    (app(LESS, BOT, x), app(LESS, BOT, x)),
    (app(LESS, x, BOT), app(LESS, x, BOT)),
    (app(LESS, BOT, quote(x)), app(LESS, BOT, quote(x))),
    (app(LESS, quote(x), BOT), app(LESS, quote(x), BOT)),
    (app(LESS, BOT, quote(TOP)), lib.true),
    (app(LESS, quote(BOT), BOT), lib.true),
    pytest.mark.xfail(
        (app(LESS, quote(TOP), quote(app(S, K, I, TOP))), lib.true),
        reason='oracle is too weak',
    ),
    pytest.mark.xfail(
        (app(LESS, quote(app(S, K, I, BOT)), quote(BOT)), lib.true),
        reason='oracle is too weak',
    ),
    pytest.mark.xfail(
        (app(LESS, quote(app(S, I, I, app(S, I, I))), quote(BOT)), lib.true),
        reason='oracle is too weak',
    ),
]


@for_each(REDUCE_EXAMPLES)
def test_reduce(code, expected_result):
    with xfail_if_not_implemented():
        actual_result = continuation.reduce(code, BUDGET)
    assert actual_result == expected_result


@for_each(iter_equations(['sk', 'join'], test_id='continuation'))
def test_reduce_equations(code, expected, message):
    with xfail_if_not_implemented():
        actual = continuation.reduce(code)
    assert actual == expected, message


@hypothesis.given(s_codes)
def test_simplify_runs(code):
    with xfail_if_not_implemented():
        continuation.simplify(code)


@hypothesis.given(s_quoted)
def test_simplify_runs_quoted(quoted):
    with xfail_if_not_implemented():
        continuation.simplify(quoted)
