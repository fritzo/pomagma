from pomagma.reducer import engine
from pomagma.reducer import lib
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import CODE, EVAL, QQUOTE, QAPP, EQUAL, LESS
from pomagma.reducer.code import UNIT, BOOL, MAYBE
from pomagma.reducer.code import VAR, APP, QUOTE
from pomagma.reducer.sugar import app, join, quote, qapp, combinator
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s
import pytest

BUDGET = 10000

w = VAR('w')
x = VAR('x')
y = VAR('y')
z = VAR('z')
F = app(K, I)


@for_each([
    (None, None, 0),
    (None, None, 0),
    (None, (x, None), 3),
    (None, (y, (x, None)), 6),
    ((I, None), None, 2),
    ((I, None), (x, None), 2 + 3),
    ((I, None), (y, (x, None)), 2 + 6),
    ((x, None), None, 3),
    ((x, None), (x, None), 3 + 3),
    ((x, None), (y, (x, None)), 3 + 6),
    ((x, (I, None)), None, 5),
    ((x, (I, None)), (x, None), 5 + 3),
    ((x, (I, None)), (y, (x, None)), 5 + 6),
])
def test_context_complexity(stack, bound, expected):
    context = engine.Context(stack=stack, bound=bound)
    assert engine.context_complexity(context) == expected


@combinator
def map_(f, xs):
    return app(xs, lib.nil, lambda h, t: lib.cons(app(f, h), map_(f, t)))


def box(item):
    return app(C, I, item)


def enum(items):
    return join(*map(box, items))


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
    (app(I, K), K),
    (K, K),
    (app(K, x), app(K, x)),
    (app(K, x, y), x),
    (app(K, x, y, z), app(x, z)),
    (B, B),
    (app(B, x), app(B, x)),
    (app(B, x, y), app(B, x, y)),
    (app(B, x, y, z), app(x, app(y, z))),
    (app(B, x, y, z, w), app(x, app(y, z), w)),
    (C, C),
    (app(C, x), app(C, x)),
    (app(C, x, y), app(C, x, y)),
    (app(C, x, y, z), app(x, z, y)),
    (app(C, x, y, z, w), app(x, z, y, w)),
    (S, S),
    (app(S, x), app(S, x)),
    (app(S, x, y), app(S, x, y)),
    (app(S, x, y, z), app(x, z, app(y, z))),
    (app(S, x, y, z, w), app(x, z, app(y, z), w)),
    (J, J),
    (app(J, x), app(J, x)),
    (join(x, y), join(x, y)),
    (join(x, x), x),
    (join(BOT, x), x),
    (join(TOP, x), TOP),
    (join(K, APP(K, I)), J),
    (join(APP(K, I), K), J),
    (join(J, K), J),
    (join(K, J), J),
    (join(J, APP(K, I)), J),
    (join(APP(K, I), J), J),
    (app(C, J), J),
    (app(S, J, I), I),
    (app(join(x, y), z), join(app(x, z), app(y, z))),
    (app(join(I, app(K, I)), I), I),
    (app(join(I, app(K, I)), K), join(I, K)),
    (enum([I]), enum([I])),
    (enum([I, I]), enum([I])),
    (enum([I, BOT]), enum([I])),
    (enum([I, TOP]), enum([TOP])),
    (enum([BOT, I, TOP]), enum([TOP])),
    (enum([K, F]), enum([K, F])),
    (enum([BOT, K, F]), enum([K, F])),
    (enum([K, F, J]), enum([J])),
    (enum([K, F, TOP]), enum([TOP])),
    (enum([BOT, box(BOT)]), enum([box(BOT)])),
    (enum([BOT, box(BOT), box(box(BOT))]), enum([box(box(BOT))])),
    (enum([BOT, box(BOT), box(box(BOT)), box(TOP)]), enum([box(TOP)])),
    (app(lib.list_map, I, lib.nil), lib.nil),
    (map_(I, lib.nil), lib.nil),
    (map_(I, lib.cons(x, lib.nil)), lib.cons(x, lib.nil)),
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
    (UNIT, UNIT),
    (app(UNIT, x), app(UNIT, x)),
    (app(UNIT, app(UNIT, x)), app(UNIT, x)),
    (app(UNIT, TOP), TOP),
    (app(UNIT, BOT), BOT),
    (app(UNIT, I), I),
    (app(UNIT, K), TOP),
    (app(UNIT, B), TOP),
    (app(UNIT, C), TOP),
    (app(UNIT, S), TOP),
    (app(UNIT, J), TOP),
    (app(BOOL, x), app(BOOL, x)),
    (app(BOOL, app(BOOL, x)), app(BOOL, x)),
    (app(BOOL, TOP), TOP),
    (app(BOOL, BOT), BOT),
    (app(BOOL, K), K),
    (app(BOOL, APP(K, I)), APP(K, I)),
    (app(BOOL, I), TOP),
    (app(BOOL, B), TOP),
    (app(BOOL, C), TOP),
    (app(BOOL, S), TOP),
    (app(BOOL, J), TOP),
    (app(MAYBE, x), app(MAYBE, x)),
    (app(MAYBE, app(MAYBE, x)), app(MAYBE, x)),
    (app(MAYBE, TOP), TOP),
    (app(MAYBE, BOT), BOT),
    (app(MAYBE, K), K),
    (app(MAYBE, app(K, app(C, I, TOP))), app(K, app(C, I, TOP))),
    (app(MAYBE, app(K, app(C, I, BOT))), app(K, app(C, I, BOT))),
    (app(MAYBE, app(K, app(C, I, I))), app(K, app(C, I, I))),
    (app(MAYBE, I), TOP),
    (app(MAYBE, B), TOP),
    (app(MAYBE, C), TOP),
    (app(MAYBE, S), TOP),
    (app(MAYBE, J), TOP),
    (app(CODE, x), app(CODE, x)),
    (app(CODE, app(CODE, x)), app(CODE, x)),
    (app(CODE, TOP), TOP),
    (app(CODE, BOT), BOT),
    (app(CODE, QUOTE(x)), QUOTE(x)),
    (app(CODE, QUOTE(TOP)), QUOTE(TOP)),
    (app(CODE, QUOTE(BOT)), QUOTE(BOT)),
    (app(CODE, QUOTE(I)), QUOTE(I)),
    (app(CODE, QUOTE(QUOTE(x))), QUOTE(QUOTE(x))),
    (app(CODE, app(QQUOTE, x)), app(QQUOTE, x)),
    (app(CODE, qapp(x, y)), qapp(x, y)),
]


@for_each(REDUCE_EXAMPLES)
def test_reduce(code, expected_result):
    actual_result = engine.reduce(code, BUDGET)
    assert actual_result == expected_result


alphabet = '_abcdefghijklmnopqrstuvwxyz'
s_vars = s.builds(
    VAR,
    s.builds(str, s.text(alphabet=alphabet, min_size=1, average_size=5)),
)
s_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
    s.just(J),
    s.one_of(
        s.just(CODE),
        s.just(EVAL),
        s.just(QAPP),
        s.just(QQUOTE),
        s.just(EQUAL),
        s.just(LESS),
    ),
    s.one_of(
        s.just(UNIT),
        s.just(BOOL),
        s.just(MAYBE),
    ),
)


def s_codes_extend(codes):
    return s.one_of(
        s.builds(APP, codes, codes),
        s.builds(QUOTE, codes),
    )


s_codes = s.recursive(s_atoms, s_codes_extend, max_leaves=100)
s_quoted = s.builds(quote, s_codes)


@hypothesis.given(s_codes)
def test_simplify_runs(code):
    engine.simplify(code)


@hypothesis.given(s_quoted)
def test_simplify_runs_quoted(quoted):
    engine.simplify(quoted)
