from pomagma.reducer import lib
from pomagma.reducer.code import VAR
from pomagma.reducer.engine import simplify
from pomagma.reducer.sugar import as_code, app
import pytest

f = VAR('f')
x = VAR('x')
y = VAR('y')

error = lib.error
undefined = lib.undefined

INTRO_FORM_EXAMPLES = [
    ('void', lambda x: x),
    ('true', lambda x, y: x),
    ('false', lambda x, y: y),
    ('none', lambda f, g: f),
    ('some', lambda x, f, g: app(g, x)),
    ('pair', lambda x, y, f: app(f, x, y)),
    ('inl', lambda x, f, g: app(f, x)),
    ('inr', lambda y, f, g: app(g, y)),
    ('zero', lambda z, s: z),
    ('succ', lambda n, z, s: app(s, n)),
    ('nil', lambda n, c: n),
    ('cons', lambda head, tail, n, c: app(c, head, tail)),
]


@pytest.mark.parametrize('name,native', INTRO_FORM_EXAMPLES)
def test_intro_forms(name, native):
    assert as_code(getattr(lib, name)) == as_code(native)


def test_unit():
    assert simplify(lib.unit_test(lib.void, f)) == f
    assert simplify(lib.unit_test(error, f)) == error
    assert simplify(lib.unit_test(undefined, f)) == undefined


def test_bool():
    t = lib.true
    f = lib.false
    assert simplify(lib.bool_test(t, x)) == x
    assert simplify(lib.bool_test(f, x)) == x
    assert simplify(lib.bool_test(error, x)) == error
    assert simplify(lib.bool_test(undefined, x)) == undefined
    assert simplify(lib.bool_not(t)) == f
    assert simplify(lib.bool_not(f)) == t
    assert simplify(lib.bool_and(t, t)) == t
    assert simplify(lib.bool_and(t, f)) == f
    assert simplify(lib.bool_and(f, t)) == f
    assert simplify(lib.bool_and(f, f)) == f
    assert simplify(lib.bool_or(t, t)) == t
    assert simplify(lib.bool_or(t, f)) == t
    assert simplify(lib.bool_or(f, t)) == t
    assert simplify(lib.bool_or(f, f)) == f


def test_maybe():
    assert simplify(lib.maybe_test(lib.none, f)) == f
    assert simplify(lib.maybe_test(lib.some(x), f)) == f
    assert simplify(lib.maybe_test(error, f)) == error
    assert simplify(lib.maybe_test(undefined, f)) == undefined


def test_prod():
    xy = lib.pair(x, y)
    assert simplify(lib.prod_test(xy, f)) == f
    assert simplify(lib.prod_test(error, f)) == error
    assert simplify(lib.prod_test(undefined, f)) == undefined
    assert simplify(lib.prod_fst(xy)) == x
    assert simplify(lib.prod_snd(xy)) == y


def test_sum():
    assert simplify(lib.sum_test(lib.inl(x), f)) == f
    assert simplify(lib.sum_test(lib.inr(y), f)) == f
    assert simplify(lib.sum_test(error, f)) == error
    assert simplify(lib.sum_test(undefined, f)) == undefined


def test_num():
    succ = lib.succ
    zero = lib.zero
    one = succ(zero)
    two = succ(one)
    three = succ(two)
    assert simplify(lib.num_test(zero, f)) == f
    assert simplify(lib.num_test(one, f)) == f
    assert simplify(lib.num_test(error, f)) == error
    assert simplify(lib.num_test(succ(error), f)) == error
    assert simplify(lib.num_test(succ(succ(error)), f)) == error
    assert simplify(lib.num_test(undefined, f)) == undefined
    assert simplify(lib.num_test(succ(undefined), f)) == undefined
    assert simplify(lib.num_test(succ(succ(undefined)), f)) == undefined
    assert simplify(lib.num_pred(zero)) == error
    assert simplify(lib.num_pred(one)) == zero
    assert simplify(lib.num_pred(two)) == one
    assert simplify(lib.num_pred(three)) == two
    assert simplify(lib.num_add(zero, zero)) == zero
    assert simplify(lib.num_add(one, zero)) == one
    assert simplify(lib.num_add(two, zero)) == two
    assert simplify(lib.num_add(three, zero)) == three


@pytest.mark.xfail
def test_num_xfail():
    succ = lib.succ
    zero = lib.zero
    one = succ(zero)
    two = succ(one)
    three = succ(two)
    assert simplify(lib.num_test(two, f)) == f
    assert simplify(lib.num_test(three, f)) == f
    assert simplify(lib.num_add(zero, two)) == two
    assert simplify(lib.num_add(zero, three)) == three
    assert simplify(lib.num_add(zero, one)) == one
    assert simplify(lib.num_add(one, one)) == two
    assert simplify(lib.num_add(one, two)) == three
    assert simplify(lib.num_add(two, one)) == three
