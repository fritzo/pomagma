from cStringIO import StringIO
from pomagma.reducer.code import APP, ABS, JOIN, QUOTE, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import CODE, EVAL, QAPP, QQUOTE, EQUAL, LESS
from pomagma.reducer.code import NVAR, IVAR, FUN, LET
from pomagma.reducer.code import V, A, UNIT, BOOL, MAYBE, PROD, SUM, NUM
from pomagma.reducer.code_test import s_codes
from pomagma.reducer.serial import dump, load
from pomagma.reducer.serial import pack_head_argc, unpack_head_argc
from pomagma.reducer.serial import pack_varint, unpack_varint
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s
import pytest


@hypothesis.given(s.integers())
@hypothesis.settings(max_examples=1000)
def test_pack_unpack_varint(n):
    hypothesis.assume(n >= 0)
    chars = list(pack_varint(n))
    iter_chars = iter(chars)
    actual = unpack_varint(iter_chars)
    assert actual == n, chars
    with pytest.raises(StopIteration):
        next(iter_chars)


@hypothesis.given(s.integers(), s.integers())
@hypothesis.settings(max_examples=1000)
def test_pack_unpack_head_argc(head, argc):
    hypothesis.assume(head >= 0)
    hypothesis.assume(argc >= 0)
    chars = list(pack_head_argc(head, argc))
    iter_chars = iter(chars)
    actual_head, actual_argc = unpack_head_argc(iter_chars)
    assert actual_head == head, chars
    assert actual_argc == argc, chars
    with pytest.raises(StopIteration):
        next(iter_chars)


x = NVAR('x')


@for_each([
    x,
    NVAR('the_quick_brown_fox_jumped_over_the_lazy_dog'),
    NVAR('take_one_down_and_pass_it_around_and_' * 9),
    NVAR('take_one_down_and_pass_it_around_and_' * 99),
    NVAR('take_one_down_and_pass_it_around_and_' * 999),
    IVAR(0),
    IVAR(1),
    IVAR(2),
    TOP,
    BOT,
    I,
    K,
    B,
    C,
    S,
    CODE,
    EVAL,
    QAPP,
    QQUOTE,
    EQUAL,
    LESS,
    V,
    A,
    UNIT,
    BOOL,
    MAYBE,
    PROD,
    SUM,
    NUM,
    ABS(IVAR(0)),
    APP(IVAR(0), x),
    APP(K, I),
    APP(APP(B, C), S),
    APP(APP(APP(S, K), I), B),
    JOIN(I, K),
    JOIN(APP(K, I), K),
    APP(JOIN(APP(K, I), K), I),
    QUOTE(K),
    APP(QUOTE(K), C),
    FUN(x, APP(S, APP(x, x))),
    APP(FUN(x, x), I),
    LET(x, I, APP(APP(S, x), x)),
])
def test_serialize_deserialize_parametrized(code):
    f_out = StringIO()
    dump(code, f_out)
    serialized = f_out.getvalue()
    print(' '.join('{:02x}'.format(ord(c)) for c in serialized))
    f_out.close()

    f_in = StringIO(serialized)
    actual = load(f_in)
    f_in.close()

    assert actual == code


@hypothesis.given(s_codes)
@hypothesis.settings(max_examples=1000)
def test_serialize_deserialize_property_based(code):
    f_out = StringIO()
    dump(code, f_out)
    serialized = f_out.getvalue()
    print(' '.join('{:02x}'.format(ord(c)) for c in serialized))
    f_out.close()

    f_in = StringIO(serialized)
    actual = load(f_in)
    f_in.close()

    assert actual == code
