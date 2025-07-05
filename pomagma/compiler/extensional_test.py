from pomagma.compiler import __main__ as main
from pomagma.compiler.expressions import Expression
from pomagma.compiler.extensional import (
    APP,
    CB,
    COMP,
    JOIN,
    RAND,
    B,
    C,
    I,
    J,
    K,
    R,
    S,
    W,
    iter_closure_maps,
    iter_eta_substitutions,
    iter_subsets,
)
from pomagma.compiler.util import find_theories
from pomagma.util.testing import for_each


def lam(v, e):
    return e.abstract(v)


def test_abstraction():
    x = Expression("x")
    y = Expression("y")
    z = Expression("z")

    assert lam(x, x) == I
    assert lam(x, y) == APP(K, y)

    assert lam(y, APP(APP(x, y), y)) == APP(W, x)
    assert lam(z, APP(APP(x, z), APP(y, z))) == APP(APP(S, x), y)
    assert lam(z, APP(APP(x, z), y)) == APP(APP(C, x), y)
    assert lam(z, APP(x, APP(y, z))) == COMP(x, y)

    assert lam(z, COMP(APP(x, z), APP(y, z))) == APP(APP(S, COMP(B, x)), y)
    assert lam(z, COMP(APP(x, z), y)) == COMP(APP(CB, y), x)
    assert lam(z, COMP(x, APP(y, z))) == COMP(APP(B, x), y)
    assert lam(y, COMP(x, y)) == APP(B, x)
    assert lam(x, COMP(x, y)) == APP(CB, y)

    assert lam(z, JOIN(APP(x, z), APP(y, z))) == JOIN(x, y)
    assert lam(z, JOIN(x, APP(y, z))) == COMP(APP(J, x), y)
    assert lam(z, JOIN(APP(x, z), y)) == COMP(APP(J, y), x)
    assert lam(y, JOIN(x, y)) == APP(J, x)
    assert lam(x, JOIN(x, y)) == APP(J, y)

    assert lam(z, RAND(APP(x, z), APP(y, z))) == RAND(x, y)
    assert lam(z, RAND(x, APP(y, z))) == COMP(APP(R, x), y)
    assert lam(z, RAND(APP(x, z), y)) == COMP(APP(R, y), x)
    assert lam(y, RAND(x, y)) == APP(R, x)
    assert lam(x, RAND(x, y)) == APP(R, y)


def test_iter_subsets():
    actual = set(map(frozenset, iter_subsets(list(range(3)))))
    expected = set(
        map(
            frozenset,
            [
                [],
                [1],
                [2],
                [1, 2],
                [0],
                [0, 1],
                [0, 2],
                [0, 1, 2],
            ],
        )
    )
    assert actual == expected


def test_iter_eta_substitutions():
    a = Expression("a")
    x = Expression("x")
    actual = set(iter_eta_substitutions(x))
    expected = {x, a.abstract(a), APP(x, a).abstract(a)}
    assert actual == expected


def test_iter_closure_maps():
    x = Expression("x")
    y = Expression("y")
    assert set(iter_closure_maps(x)) == {I}
    assert set(iter_closure_maps(APP(x, x))) == {APP(W, I)}
    assert set(iter_closure_maps(APP(x, y))) == {I, APP(C, I), APP(W, I)}


def iter_close_rules():
    blacklist = [
        # not abstractable:
        "group.theory",
        "h4.theory",
        # no validator implemented:
        "quote.theory",
    ]
    for filename in find_theories():
        is_extensional = filename.split("/")[-1] not in blacklist
        yield filename, is_extensional


@for_each(iter_close_rules())
def test_close_rules(filename, is_extensional):
    main.test_close_rules(filename, is_extensional)
