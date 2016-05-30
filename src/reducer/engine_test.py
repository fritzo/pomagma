from pomagma.reducer import engine
from pomagma.reducer import lib
from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, VAR
from pomagma.reducer.sugar import app
import pytest
import sys

BUDGET = 10000

w = VAR('w')
x = VAR('x')
y = VAR('y')
z = VAR('z')


def map_(f, xs):
    return app(xs, lib.nil, lambda h, t: lib.cons(app(f, h), app(map_, f, t)))


EXAMPLES = [
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
    (map_(I, lib.nil), lib.nil),
    (map_(I, lib.cons(x, lib.nil)), lib.cons(x, lib.nil)),
]


@pytest.mark.parametrize('code,expected_result', EXAMPLES)
def test_reduce(code, expected_result):
    actual_result = engine.reduce(code, BUDGET)
    assert actual_result == expected_result


# Debugging.
if __name__ == '__main__':
    sys.setrecursionlimit(100)
    engine.reduce(app(map_, I, lib.nil))
