from pomagma.reducer import lib
from pomagma.reducer.code import VAR
from pomagma.reducer.engine import simplify
from pomagma.reducer.sugar import as_code, app
import pytest

f = VAR('f')
x = VAR('x')
y = VAR('y')

ok = lib.ok
error = lib.error
undefined = lib.undefined
true = lib.true
false = lib.false

INTRO_FORM_EXAMPLES = [
    ('ok', lambda x: x),
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
    assert simplify(lib.unit_test(ok)) == ok
    assert simplify(lib.unit_test(error)) == error
    assert simplify(lib.unit_test(undefined)) == undefined
    assert simplify(lib.unit_and(ok, ok)) == ok
    assert simplify(lib.unit_and(ok, undefined)) == undefined
    assert simplify(lib.unit_and(undefined, ok)) == undefined
    assert simplify(lib.unit_and(undefined, undefined)) == undefined
    assert simplify(lib.unit_or(ok, ok)) == ok
    assert simplify(lib.unit_or(ok, undefined)) == ok
    assert simplify(lib.unit_or(undefined, ok)) == ok
    assert simplify(lib.unit_or(undefined, undefined)) == undefined


def test_bool():
    assert simplify(lib.bool_test(true)) == ok
    assert simplify(lib.bool_test(false)) == ok
    assert simplify(lib.bool_test(error)) == error
    assert simplify(lib.bool_test(undefined)) == undefined
    assert simplify(lib.bool_not(true)) == false
    assert simplify(lib.bool_not(false)) == true
    assert simplify(lib.bool_and(true, true)) == true
    assert simplify(lib.bool_and(true, false)) == false
    assert simplify(lib.bool_and(false, true)) == false
    assert simplify(lib.bool_and(false, false)) == false
    assert simplify(lib.bool_or(true, true)) == true
    assert simplify(lib.bool_or(true, false)) == true
    assert simplify(lib.bool_or(false, true)) == true
    assert simplify(lib.bool_or(false, false)) == false


def test_maybe():
    assert simplify(lib.maybe_test(lib.none)) == ok
    assert simplify(lib.maybe_test(lib.some(x))) == ok
    assert simplify(lib.maybe_test(error)) == error
    assert simplify(lib.maybe_test(undefined)) == undefined


def test_prod():
    xy = lib.pair(x, y)
    assert simplify(lib.prod_test(xy)) == ok
    assert simplify(lib.prod_test(error)) == error
    assert simplify(lib.prod_test(undefined)) == undefined
    assert simplify(lib.prod_fst(xy)) == x
    assert simplify(lib.prod_snd(xy)) == y


def test_sum():
    assert simplify(lib.sum_test(lib.inl(x))) == ok
    assert simplify(lib.sum_test(lib.inr(y))) == ok
    assert simplify(lib.sum_test(error)) == error
    assert simplify(lib.sum_test(undefined)) == undefined


def test_num():
    succ = lib.succ
    zero = lib.zero
    one = succ(zero)
    two = succ(one)
    three = succ(two)
    assert simplify(lib.num_test(zero)) == ok
    assert simplify(lib.num_test(one)) == ok
    assert simplify(lib.num_test(error)) == error
    assert simplify(lib.num_test(succ(error))) == error
    assert simplify(lib.num_test(succ(succ(error)))) == error
    assert simplify(lib.num_test(undefined)) == undefined
    assert simplify(lib.num_test(succ(undefined))) == undefined
    assert simplify(lib.num_test(succ(succ(undefined)))) == undefined
    assert simplify(lib.num_pred(zero)) == error
    assert simplify(lib.num_pred(one)) == zero
    assert simplify(lib.num_pred(two)) == one
    assert simplify(lib.num_pred(three)) == two
    assert simplify(lib.num_add(zero, zero)) == zero
    assert simplify(lib.num_add(one, zero)) == one
    assert simplify(lib.num_add(two, zero)) == two
    assert simplify(lib.num_add(three, zero)) == three
    assert simplify(lib.num_less(zero, zero)) == false
    assert simplify(lib.num_less(zero, one)) == true
    assert simplify(lib.num_less(zero, two)) == true
    assert simplify(lib.num_less(one, zero)) == false
    assert simplify(lib.num_less(one, one)) == false
    assert simplify(lib.num_less(one, two)) == true
    assert simplify(lib.num_less(two, zero)) == false
    assert simplify(lib.num_less(two, one)) == false


@pytest.mark.xfail
def test_num_xfail():
    succ = lib.succ
    zero = lib.zero
    one = succ(zero)
    two = succ(one)
    three = succ(two)
    assert simplify(lib.num_test(two)) == ok
    assert simplify(lib.num_test(three)) == ok
    assert simplify(lib.num_add(zero, two)) == two
    assert simplify(lib.num_add(zero, three)) == three
    assert simplify(lib.num_add(zero, one)) == one
    assert simplify(lib.num_add(one, one)) == two
    assert simplify(lib.num_add(one, two)) == three
    assert simplify(lib.num_add(two, one)) == three
    assert simplify(lib.num_less(two, two)) == false


def test_list():
    nil = lib.nil
    cons = lib.cons
    assert simplify(lib.list_test(nil)) == ok
    assert simplify(lib.list_test(cons(x, nil))) == ok
    assert simplify(lib.list_test(error)) == error
    assert simplify(lib.list_test(undefined)) == undefined
    assert simplify(lib.list_test(cons(x, error))) == error
    assert simplify(lib.list_test(cons(x, undefined))) == undefined
    assert simplify(lib.list_empty(nil)) == true
    assert simplify(lib.list_empty(cons(x, nil))) == false
