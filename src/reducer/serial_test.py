from StringIO import StringIO
from hypothesis.strategies import integers
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, APP, JOIN
from pomagma.reducer.serial import dump, load
from pomagma.reducer.serial import pack_head_argc, unpack_head_argc
from pomagma.reducer.serial import pack_varint, unpack_varint
from pomagma.util.testing import for_each
import hypothesis
import pytest


@hypothesis.given(integers())
@hypothesis.settings(max_examples=1000)
def test_pack_unpack_varint(n):
    hypothesis.assume(n >= 0)
    chars = list(pack_varint(n))
    iter_chars = iter(chars)
    actual = unpack_varint(iter_chars)
    assert actual == n, chars
    with pytest.raises(StopIteration):
        next(iter_chars)


@hypothesis.given(integers(), integers())
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


@for_each([
    TOP,
    BOT,
    I,
    K,
    B,
    C,
    S,
    APP(K, I),
    APP(APP(B, C), S),
    APP(APP(APP(S, K), I), B),
    JOIN(I, K),
    JOIN(APP(K, I), K),
    APP(JOIN(APP(K, I), K), I),
])
def test_serialize_deserialize(code):
    f_out = StringIO()
    dump(code, f_out)
    serialized = f_out.getvalue()
    print(' '.join('{:02x}'.format(ord(c)) for c in serialized))
    f_out.close()

    f_in = StringIO(serialized)
    actual = load(f_in)
    f_in.close()

    assert actual == code