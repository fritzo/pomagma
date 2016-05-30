from pomagma.reducer import engine
from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, VAR
from pomagma.reducer.sugar import app
import pytest

BUDGET = 10000

x = VAR('x')
y = VAR('y')
z = VAR('z')

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
    (B, B),
    (app(B, x), app(B, x)),
    (app(B, x, y), app(B, x, y)),
    (app(B, x, y, z), app(x, app(y, z))),
    (C, C),
    (app(C, x), app(C, x)),
    (app(C, x, y), app(C, x, y)),
    (app(C, x, y, z), app(x, z, y)),
    (S, S),
    (app(S, x), app(S, x)),
    (app(S, x, y), app(S, x, y)),
    (app(S, x, y, z), app(x, z, app(y, z))),
]


@pytest.mark.parametrize('code,expected_result', EXAMPLES)
def test_reduce(code, expected_result):
    actual_result = engine.reduce(code, BUDGET)
    assert actual_result == expected_result
