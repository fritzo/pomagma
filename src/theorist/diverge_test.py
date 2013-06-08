from nose.tools import assert_equal, assert_raises
from pomagma.theorist.diverge import I, K, B, C, W, S, TOP
from pomagma.theorist.diverge import diverge_step, Converged


a, b, c = ['a'], ['b'], ['c']  # argument lists
x, y, z = 'x', 'y', 'z'  # arguments


STEPS = [
    ([I], [TOP]),
    ([I, a], a),
    ([I, [x], a], [x, a]),

    ([K], [TOP]),
    ([K, a], a),
    ([K, a, b], a),
    ([K, [x], b, c], [x, c]),

    ([B], [TOP]),
    ([B, a], a),
    ([B, [x], [y]], [x, [y, [TOP]]]),
    ([B, [x], [y], a], [x, [y, a]]),
    ([B, [x], [y], a, b], [x, [y, a], b]),

    ([C], [TOP]),
    ([C, a], a),
    ([C, [x], a], [x, [TOP], a]),
    ([C, [x], a, b], [x, b, a]),
    ([C, [x], a, b, c], [x, b, a, c]),

    ([W], [TOP]),
    ([W, [x]], [x, [TOP], [TOP]]),
    ([W, [x], a], [x, a, a]),
    ([W, [x], a, b], [x, a, a, b]),

    ([S], [TOP]),
    ([S, [x]], [x, [TOP], [TOP]]),
    ([S, [x], [y]], [x, [TOP], [y, [TOP]]]),
    ([S, [x], [y], a], [x, a, [y, a]]),
    ([S, [x], [y], a, b], [x, a, [y, a], b]),
    ]


def _test_diverge_step(term, expected):
    actual = diverge_step(term)
    assert_equal(expected, actual)


def test_diverge_step():
    for term, expected in STEPS:
        yield _test_diverge_step, term, expected


def test_converge():
    assert_raises(Converged, diverge_step, [TOP])
