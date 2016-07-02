from pomagma.reducer import engine
from pomagma.reducer import lib
from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import EVAL, EQUAL, LESS
from pomagma.reducer.code import VAR
from pomagma.reducer.sugar import app, join, quote, qapp, combinator
from pomagma.util.testing import for_each
import pytest
import sys

BUDGET = 10000

w = VAR('w')
x = VAR('x')
y = VAR('y')
z = VAR('z')


@combinator
def map_(f, xs):
    return app(xs, lib.nil, lambda h, t: lib.cons(app(f, h), map_(f, t)))


@for_each([
    (x, x),
    (app(x, y), app(x, y)),
    (app(x, I), app(x, I)),
    (HOLE, HOLE),
    (app(HOLE, x), HOLE),
    (app(HOLE, x, y), HOLE),
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
    (join(x, y), join(x, y)),
    (join(x, x), x),
    (join(BOT, x), x),
    (join(TOP, x), TOP),
    (join(HOLE, x), join(HOLE, x)),
    (app(join(x, y), z), join(app(x, z), app(y, z))),
    (app(join(I, app(K, I)), I), I),
    (app(join(I, app(K, I)), K), join(I, K)),
    (app(lib.list_map, I, lib.nil), lib.nil),
    (map_(I, lib.nil), lib.nil),
    (map_(I, lib.cons(x, lib.nil)), lib.cons(x, lib.nil)),
    (quote(x), quote(x)),
    (quote(app(I, x)), quote(x)),
    (app(EVAL, x), app(EVAL, x)),
    (app(EVAL, quote(I), x), x),
    (quote(app(EVAL, quote(app(K, I, I)))), quote(I)),
    (app(S, K, K, quote(app(EVAL, quote(app(K, I, I))))), quote(I)),
    (qapp(x, y), qapp(x, y)),
    (qapp(quote(x), y), qapp(quote(x), y)),
    (qapp(x, quote(y)), qapp(x, quote(y))),
    (qapp(quote(x), quote(y)), quote(app(x, y))),
    pytest.mark.xfail(
        (qapp(quote(lib.list_map), quote(I), quote(lib.nil)), quote(lib.nil))),
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
])
def test_reduce(code, expected_result):
    actual_result = engine.reduce(code, BUDGET)
    assert actual_result == expected_result


# Debugging.
if __name__ == '__main__':
    sys.setrecursionlimit(100)
    engine.reduce(app(map_, I, lib.nil))
