import os
import glob
from nose.tools import assert_equal, assert_set_equal
from pomagma.compiler.extensional import *
from pomagma.compiler import run


def test_abstraction():
    x = Expression('x')
    y = Expression('y')
    z = Expression('z')
    lam = lambda v, e: e.abstract(v)
    assert_equal(lam(x, x), I)
    assert_equal(lam(x, y), APP(K, y))


def test_iter_subsets():
    assert_set_equal(
            set(map(frozenset, iter_subsets(range(3)))),
            set(map(frozenset, [
                [],
                [1,],
                [2,],
                [1,2,],
                [0,],
                [0,1,],
                [0,2,],
                [0,1,2,],
                ])))


def test_iter_eta_substitutions():
    a = Expression('a')
    x = Expression('x')
    y = Expression('y')
    assert_set_equal(
        set(iter_eta_substitutions(x)),
        set([
            x.abstract(a),
            a.abstract(a),
            APP(x, a).abstract(a),
            ]))


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


def _test_close_rules(filename):
    run.test_close_rules(filename)


def test_close_rules():
    for filename in glob.glob('../theory/*.rules'):
        yield _test_close_rules, filename
