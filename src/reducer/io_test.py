from pomagma.reducer import io
from pomagma.reducer import lib
from pomagma.reducer.code import I, K, B, C, APP
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies
import pomagma.reducer.code
import pytest


# ----------------------------------------------------------------------------
# Parametrized tests

EXAMPLES_BY_TYPE = {
    'unit': {
        'ok': [(lib.ok, None)],
        'encode_error': [True, False, 0, 1, 2, [None], [True]],
        'decode_error': [K, B, C, APP(C, B)],
    },
    'bool': {
        'ok': [(lib.true, True), (lib.false, False)],
        'encode_error': [None, 0, 1, 2, [None], [True]],
        'decode_error': [I, B, C, APP(C, B)],
    },
    'num': {
        'ok': [
            (lib.zero, 0),
            (lib.succ(lib.zero), 1),
            (lib.succ(lib.succ(lib.zero)), 2),
            (lib.succ(lib.succ(lib.succ(lib.zero))), 3),
        ],
        'encode_error': [None, False, True, [0], [True]],
    },
    ('prod', 'bool', 'num'): {
        'ok': [
            (lib.pair(lib.true, lib.zero), (True, 0)),
            (lib.pair(lib.false, lib.succ(lib.succ(lib.zero))), (False, 2)),
        ],
        'encode_error': [None, (), (True,), [True, 0], True, 0, 'asdf']
    },
    ('sum', 'bool', 'num'): {
        'ok': [
            (lib.inl(lib.true), (True, True)),
            (lib.inl(lib.false), (True, False)),
            (lib.inr(lib.zero), (False, 0)),
            (lib.inr(lib.succ(lib.succ(lib.zero))), (False, 2)),
        ],
        'encode_error': [None, (), (True,), [True, 0], True, 0, 'asdf']
    },
    ('maybe', 'bool'): {
        'ok': [
            (lib.none, None),
            (lib.some(lib.true), (True,)),
            (lib.some(lib.false), (False,)),
        ],
        'encode_error': [True, False, 0, 1, 2, (), 'asdf'],
        'decode_error': [I],
    },
    ('list', 'bool'): {
        'ok': [
            (lib.nil, []),
            (lib.cons(lib.true, lib.cons(lib.false, lib.nil)), [True, False]),
        ],
        'encode_error': [None, True, False, 0, 1, 2, (), 'asdf', [[True]]],
        'decode_error': [I],
    },
    ('list', ('list', 'num')): {
        'ok': [
            (lib.nil, []),
            (lib.cons(lib.nil, lib.nil), [[]]),
            (lib.cons(lib.cons(lib.zero, lib.nil), lib.nil), [[0]]),
        ],
        'encode_error': [0, [1], [[2], 3], [[[]]]],
    }
}

EXAMPLES = {
    'ok': [
        (tp, code, value)
        for tp, examples in EXAMPLES_BY_TYPE.iteritems()
        for code, value in examples.get('ok', [])
    ],
    'encode_error': [
        (tp, value)
        for tp, examples in EXAMPLES_BY_TYPE.iteritems()
        for value in examples.get('encode_error', [])
    ],
    'decode_error': [
        (tp, code)
        for tp, examples in EXAMPLES_BY_TYPE.iteritems()
        for code in examples.get('decode_error', [])
    ],
}


@for_each(EXAMPLES['ok'])
def test_encode(tp, code, value):
    encode = io.encoder(tp)
    actual_code = encode(value)
    assert actual_code == code


@for_each(EXAMPLES['ok'])
def test_decode(tp, code, value):
    decode = io.decoder(tp)
    actual_value = decode(code)
    assert actual_value == value


@for_each(EXAMPLES['encode_error'])
def test_encode_error(tp, value):
    encode = io.encoder(tp)
    with pytest.raises(TypeError):
        encode(value)


@for_each(EXAMPLES['decode_error'])
def test_decode_error(tp, code):
    decode = io.decoder(tp)
    with pytest.raises(TypeError):
        decode(code)


@for_each(EXAMPLES['ok'])
def test_serialize_parse(tp, code, value):
    string = pomagma.reducer.code.serialize(code)
    assert isinstance(string, str)
    actual_code = pomagma.reducer.code.parse(string)
    assert actual_code == code


# ----------------------------------------------------------------------------
# Property based tests

s = hypothesis.strategies

types_base = s.one_of(s.just('unit'), s.just('bool'), s.just('num'))


def types_extend(types_):
    return s.one_of(
        s.tuples(s.just('maybe'), types_),
        s.tuples(s.just('list'), types_),
        s.tuples(s.just('prod'), types_, types_),
        s.tuples(s.just('sum'), types_, types_),
    )


types = s.recursive(types_base, types_extend, max_leaves=10)


def code_of_type(tp):
    if not isinstance(tp, tuple):
        if tp == 'unit':
            return s.just(lib.ok)
        if tp == 'bool':
            return s.sampled_from([lib.true, lib.false])
        if tp == 'num':
            return s.recursive(
                s.just(lib.zero),
                lambda n: s.builds(lib.succ, n),
            )
    elif len(tp) == 2:
        if tp[0] == 'maybe':
            return s.one_of(
                s.just(lib.none),
                s.builds(lib.some, code_of_type(tp[1])),
            )
        if tp[0] == 'list':
            return s.recursive(
                s.just(lib.nil),
                lambda tail: s.builds(lib.cons, code_of_type(tp[1]), tail),
            )
    elif len(tp) == 3:
        if tp[0] == 'prod':
            return s.builds(lib.pair, code_of_type(tp[1]), code_of_type(tp[2]))
        if tp[0] == 'sum':
            return s.one_of(
                s.builds(lib.inl, code_of_type(tp[1])),
                s.builds(lib.inr, code_of_type(tp[2])),
            )
    raise ValueError(tp)


@hypothesis.strategies.composite
def type_and_data(draw):
    tp = draw(types)
    code = draw(code_of_type(tp))
    return (tp, code)


@hypothesis.given(type_and_data())
@hypothesis.settings(max_examples=1000)
def test_decode_encode(tp_code):
    tp, code = tp_code
    encode = io.encoder(tp)
    decode = io.decoder(tp)
    value = decode(code)
    actual_code = encode(value)
    assert actual_code == code
