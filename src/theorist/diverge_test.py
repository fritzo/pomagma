from nose.tools import assert_equal, assert_raises
from pomagma.theorist.diverge import (
    I,
    K,
    B,
    C,
    W,
    S,
    Y,
    TOP,
    converge_step,
    try_converge,
    Converged,
    Diverged,
    )


a, b, c = ('a',), ('b',), ('c',)  # argument lists
x, y, z = 'x', 'y', 'z'  # arguments


STEPS = [
    ((I,), (TOP,)),
    ((I, a,), a),
    ((I, (x,), a,), (x, a,)),

    ((K,), (TOP,)),
    ((K, a,), a),
    ((K, a, b,), a),
    ((K, (x,), b, c,), (x, c,)),

    ((B,), (TOP,)),
    ((B, a,), a),
    ((B, (x,), (y,),), (x, (y, (TOP,),),)),
    ((B, (x,), (y,), a,), (x, (y, a,),)),
    ((B, (x,), (y,), a, b,), (x, (y, a,), b,)),

    ((C,), (TOP,)),
    ((C, a,), a),
    ((C, (x,), a,), (x, (TOP,), a,)),
    ((C, (x,), a, b,), (x, b, a,)),
    ((C, (x,), a, b, c,), (x, b, a, c,)),

    ((W,), (TOP,)),
    ((W, (x,),), (x, (TOP,), (TOP,),)),
    ((W, (x,), a,), (x, a, a,)),
    ((W, (x,), a, b,), (x, a, a, b,)),

    ((S,), (TOP,)),
    ((S, (x,),), (x, (TOP,), (TOP,),)),
    ((S, (x,), (y,),), (x, (TOP,), (y, (TOP,),),)),
    ((S, (x,), (y,), a,), (x, a, (y, a,),)),
    ((S, (x,), (y,), a, b,), (x, a, (y, a,), b,)),

    ((Y,), (TOP,)),
    ((Y, (x,),), (x, (Y, (x,),),)),
    ((Y, (x,), a,), (x, (Y, (x,),), a,)),
    ]


def _test_converge_step(term, expected):
    actual = converge_step(term)
    assert_equal(expected, actual)


def test_converge_step():
    for term, expected in STEPS:
        yield _test_converge_step, term, expected


def test_converge():
    assert_raises(Converged, converge_step, (TOP,))


def test_diverge():
    WWW = (W, (W,), (W,),)
    assert_equal(converge_step(WWW), WWW)
    assert_raises(Diverged, try_converge, WWW, 1)