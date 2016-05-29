from pomagma.reducer import io
from pomagma.reducer.code import I, K, B, C, APP
import pomagma.reducer.code
import pytest

EXAMPLES_BY_TYPE = {
    'unit': {
        'ok': [(io.void, None)],
        'encode_error': [True, False, 0, 1, 2, [None], [True]],
        'decode_error': [K, B, C, APP(C, B)],
    },
    'bool': {
        'ok': [(io.true, True), (io.false, False)],
        'encode_error': [None, 0, 1, 2, [None], [True]],
        'decode_error': [I, B, C, APP(C, B)],
    },
    'num': {
        'ok': [
            (io.zero, 0),
            (io.succ(io.zero), 1),
            (io.succ(io.succ(io.zero)), 2),
            (io.succ(io.succ(io.succ(io.zero))), 3),
        ],
        'encode_error': [None, False, True, [0], [True]],
    },
    ('prod', 'bool', 'num'): {
        'ok': [
            (io.pair(io.true, io.zero), (True, 0)),
            (io.pair(io.false, io.succ(io.succ(io.zero))), (False, 2)),
        ],
        'encode_error': [None, (), (True,), [True, 0], True, 0, 'asdf']
    },
    ('sum', 'bool', 'num'): {
        'ok': [
            (io.inl(io.true), (True, True)),
            (io.inl(io.false), (True, False)),
            (io.inr(io.zero), (False, 0)),
            (io.inr(io.succ(io.succ(io.zero))), (False, 2)),
        ],
        'encode_error': [None, (), (True,), [True, 0], True, 0, 'asdf']
    },
    ('maybe', 'bool'): {
        'ok': [
            (io.none, None),
            (io.some(io.true), (True,)),
            (io.some(io.false), (False,)),
        ],
        'encode_error': [True, False, 0, 1, 2, (), 'asdf'],
        'decode_error': [I],
    },
    ('list', 'bool'): {
        'ok': [
            (io.nil, []),
            (io.cons(io.true, io.cons(io.false, io.nil)), [True, False]),
        ],
        'encode_error': [None, True, False, 0, 1, 2, (), 'asdf', [[True]]],
        'decode_error': [I],
    },
    ('list', ('list', 'num')): {
        'ok': [
            (io.nil, []),
            (io.cons(io.nil, io.nil), [[]]),
            (io.cons(io.cons(io.zero, io.nil), io.nil), [[0]]),
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


@pytest.mark.parametrize('tp,code,value', EXAMPLES['ok'])
def test_encode(tp, code, value):
    encode = io.encoder(tp)
    actual_code = encode(value)
    assert actual_code == code


@pytest.mark.parametrize('tp,code,value', EXAMPLES['ok'])
def test_decode(tp, code, value):
    decode = io.decoder(tp)
    actual_value = decode(code)
    assert actual_value == value


@pytest.mark.parametrize('tp,value', EXAMPLES['encode_error'])
def test_encode_error(tp, value):
    encode = io.encoder(tp)
    with pytest.raises(TypeError):
        encode(value)


@pytest.mark.parametrize('tp,code', EXAMPLES['decode_error'])
def test_decode_error(tp, code):
    decode = io.decoder(tp)
    with pytest.raises(TypeError):
        decode(code)


@pytest.mark.parametrize('tp,code,value', EXAMPLES['ok'])
def test_serialize_parse(tp, code, value):
    string = pomagma.reducer.code.serialize(code)
    assert isinstance(string, str)
    actual_code = pomagma.reducer.code.parse(string)
    assert actual_code == code
