from nose.tools import assert_equal, assert_set_equal
from pomagma.compiler import run
from pomagma.compiler.util import find_rules
from pomagma.compiler.extensional import (
    Expression,
    APP, COMP, JOIN, RAND,
    I, K, B, C, W, S, J, R,
    iter_subsets,
    iter_eta_substitutions,
    iter_closure_maps,
)


def test_abstraction():
    x = Expression('x')
    y = Expression('y')
    z = Expression('z')
    lam = lambda v, e: e.abstract(v)

    assert_equal(lam(x, x), I)
    assert_equal(lam(x, y), APP(K, y))

    assert_equal(lam(y, APP(APP(x, y), y)), APP(W, x))
    assert_equal(lam(z, APP(APP(x, z), APP(y, z))), APP(APP(S, x), y))
    assert_equal(lam(z, APP(APP(x, z), y)), APP(APP(C, x), y))
    assert_equal(lam(z, APP(x, APP(y, z))), COMP(x, y))

    assert_equal(
        lam(z, COMP(APP(x, z), APP(y, z))),
        APP(APP(S, COMP(B, x)), y))
    assert_equal(lam(z, COMP(APP(x, z), y)), COMP(APP(APP(C, B), y), x))
    assert_equal(lam(z, COMP(x, APP(y, z))), COMP(APP(B, x), y))
    assert_equal(lam(y, COMP(x, y)), APP(B, x))
    assert_equal(lam(x, COMP(x, y)), APP(APP(C, B), y))

    assert_equal(lam(z, JOIN(APP(x, z), APP(y, z))), JOIN(x, y))
    assert_equal(lam(z, JOIN(x, APP(y, z))), COMP(APP(J, x), y))
    assert_equal(lam(z, JOIN(APP(x, z), y)), COMP(APP(J, y), x))
    assert_equal(lam(y, JOIN(x, y)), APP(J, x))
    assert_equal(lam(x, JOIN(x, y)), APP(J, y))

    assert_equal(lam(z, RAND(APP(x, z), APP(y, z))), RAND(x, y))
    assert_equal(lam(z, RAND(x, APP(y, z))), COMP(APP(R, x), y))
    assert_equal(lam(z, RAND(APP(x, z), y)), COMP(APP(R, y), x))
    assert_equal(lam(y, RAND(x, y)), APP(R, x))
    assert_equal(lam(x, RAND(x, y)), APP(R, y))


def test_iter_subsets():
    assert_set_equal(
        set(map(frozenset, iter_subsets(range(3)))),
        set(map(frozenset, [
                [],
                [1],
                [2],
                [1, 2],
                [0],
                [0, 1],
                [0, 2],
                [0, 1, 2],
                ])))


def test_iter_eta_substitutions():
    a = Expression('a')
    x = Expression('x')
    assert_set_equal(
        set(iter_eta_substitutions(x)),
        set([
            x,
            a.abstract(a),
            APP(x, a).abstract(a)]))


def test_iter_closure_maps():
    x = Expression('x')
    y = Expression('y')
    assert_set_equal(
        set(iter_closure_maps(x)),
        set([I]))
    assert_set_equal(
        set(iter_closure_maps(APP(x, x))),
        set([APP(W, I)]))
    assert_set_equal(
        set(iter_closure_maps(APP(x, y))),
        set([I, APP(C, I), APP(W, I)]))


def test_close_rules():
    blacklist = [
        # not abstractable:
        'group.rules',
        'h4.rules',
        # no validator implemented:
        'quote.rules',
    ]
    for filename in find_rules():
        is_extensional = filename.split('/')[-1] not in blacklist
        yield run.test_close_rules, filename, is_extensional
