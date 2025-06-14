import hypothesis
import hypothesis.strategies
import pytest

from pomagma.reducer import data, lib
from pomagma.reducer.bohm import CB, B, C, I, K
from pomagma.reducer.syntax import polish_parse, polish_print
from pomagma.util.testing import for_each

# ----------------------------------------------------------------------------
# Parametrized tests

EXAMPLES_BY_TYPE = {
    "unit": {
        "ok": [(lib.ok, None)],
        "encode_error": [True, False, 0, 1, 2, [None], [True]],
        "decode_error": [K, B, C, CB],
    },
    "bool": {
        "ok": [(lib.true, True), (lib.false, False)],
        "encode_error": [None, 0, 1, 2, [None], [True]],
        "decode_error": [I, B, C, CB],
    },
    "byte": {
        "ok": [
            (lib.byte_table[ord(b"a")], b"a"),
            (lib.byte_table[0x00], b"\x00"),
            (lib.byte_table[0xFF], b"\xff"),
        ],
        "encode_error": [0, ["a"], "asdf"],
        "decode_error": [I, K, B, C, CB],
    },
    "num": {
        "ok": [
            (lib.zero, 0),
            (lib.succ(lib.zero), 1),
            (lib.succ(lib.succ(lib.zero)), 2),
            (lib.succ(lib.succ(lib.succ(lib.zero))), 3),
        ],
        "encode_error": [None, False, True, [0], [True]],
    },
    ("prod", "bool", "num"): {
        "ok": [
            (lib.pair(lib.true, lib.zero), (True, 0)),
            (lib.pair(lib.false, lib.succ(lib.succ(lib.zero))), (False, 2)),
        ],
        "encode_error": [None, (), (True,), [True, 0], True, 0, "asdf"],
    },
    ("sum", "bool", "num"): {
        "ok": [
            (lib.inl(lib.true), (True, True)),
            (lib.inl(lib.false), (True, False)),
            (lib.inr(lib.zero), (False, 0)),
            (lib.inr(lib.succ(lib.succ(lib.zero))), (False, 2)),
        ],
        "encode_error": [None, (), (True,), [True, 0], True, 0, "asdf"],
    },
    ("maybe", "bool"): {
        "ok": [
            (lib.none, None),
            (lib.some(lib.true), (True,)),
            (lib.some(lib.false), (False,)),
        ],
        "encode_error": [True, False, 0, 1, 2, (), "asdf"],
        "decode_error": [I],
    },
    ("list", "bool"): {
        "ok": [
            (lib.nil, []),
            (lib.cons(lib.true, lib.cons(lib.false, lib.nil)), [True, False]),
        ],
        "encode_error": [None, True, False, 0, 1, 2, (), "asdf", [[True]]],
        "decode_error": [I],
    },
    ("list", ("list", "num")): {
        "ok": [
            (lib.nil, []),
            (lib.cons(lib.nil, lib.nil), [[]]),
            (lib.cons(lib.cons(lib.zero, lib.nil), lib.nil), [[0]]),
        ],
        "encode_error": [0, [1], [[2], 3], [[[]]]],
    },
    ("bytes"): {
        "ok": [(lib.nil, b"")],
        "encode_error": [None, True, False, 0, 1, 2, (), [[True]]],
        "decode_error": [I],
    },
}

EXAMPLES = {
    "ok": [
        (tp, term, value)
        for tp, examples in list(EXAMPLES_BY_TYPE.items())
        for term, value in examples.get("ok", [])
    ],
    "encode_error": [
        (tp, value)
        for tp, examples in list(EXAMPLES_BY_TYPE.items())
        for value in examples.get("encode_error", [])
    ],
    "decode_error": [
        (tp, term)
        for tp, examples in list(EXAMPLES_BY_TYPE.items())
        for term in examples.get("decode_error", [])
    ],
}


@for_each(EXAMPLES["ok"])
def test_encode(tp, term, value):
    encode = data.encoder(tp)
    actual_term = encode(value)
    assert actual_term == term


@for_each(EXAMPLES["ok"])
def test_decode(tp, term, value):
    decode = data.decoder(tp)
    actual_value = decode(term)
    assert actual_value == value


@for_each(EXAMPLES["encode_error"])
def test_encode_error(tp, value):
    encode = data.encoder(tp)
    with pytest.raises(TypeError):
        encode(value)


@for_each(EXAMPLES["decode_error"])
def test_decode_error(tp, term):
    decode = data.decoder(tp)
    with pytest.raises(TypeError):
        decode(term)


@for_each(EXAMPLES["ok"])
def test_polish_serialize_parse(tp, term, value):
    string = polish_print(term)
    assert isinstance(string, str)
    actual_term = polish_parse(string)
    assert actual_term == term


# ----------------------------------------------------------------------------
# Property based tests

s = hypothesis.strategies

types_base = s.one_of(
    s.just("unit"),
    s.just("bool"),
    s.just("byte"),
    s.just("num"),
    s.just("bytes"),
)


def types_extend(types_):
    return s.one_of(
        s.tuples(s.just("maybe"), types_),
        s.tuples(s.just("list"), types_),
        s.tuples(s.just("prod"), types_, types_),
        s.tuples(s.just("sum"), types_, types_),
    )


types = s.recursive(types_base, types_extend, max_leaves=10)


def term_of_type(tp):
    if not isinstance(tp, tuple):
        if tp == "unit":
            return s.just(lib.ok)
        if tp == "bool":
            return s.sampled_from([lib.true, lib.false])
        if tp == "byte":
            # Use a small subset of byte values to avoid expensive __repr__ calls
            # \x00, \x01, 'a', \xff
            byte_values = [lib.byte_table[i] for i in [0, 1, 97, 255]]
            return s.sampled_from(byte_values)
        if tp == "num":
            return s.recursive(
                s.just(lib.zero),
                lambda n: s.builds(lib.succ, n),
                max_leaves=5,
            )
        if tp == "bytes":
            return term_of_type(("list", "byte"))
    elif len(tp) == 2:
        if tp[0] == "maybe":
            return s.one_of(
                s.just(lib.none),
                s.builds(lib.some, term_of_type(tp[1])),
            )
        if tp[0] == "list":
            return s.recursive(
                s.just(lib.nil),
                lambda tail: s.builds(lib.cons, term_of_type(tp[1]), tail),
                max_leaves=5,
            )
    elif len(tp) == 3:
        if tp[0] == "prod":
            return s.builds(lib.pair, term_of_type(tp[1]), term_of_type(tp[2]))
        if tp[0] == "sum":
            return s.one_of(
                s.builds(lib.inl, term_of_type(tp[1])),
                s.builds(lib.inr, term_of_type(tp[2])),
            )
    raise ValueError(tp)


@hypothesis.strategies.composite
def type_and_data(draw):
    tp = draw(types)
    term = draw(term_of_type(tp))
    return (tp, term)


@hypothesis.given(type_and_data())
@hypothesis.settings(max_examples=1000)
def test_decode_encode(tp_term):
    tp, term = tp_term
    encode = data.encoder(tp)
    decode = data.decoder(tp)
    value = decode(term)
    actual_term = encode(value)
    assert actual_term == term
