from pomagma.reducer.io import I, K, B, C, APP, KI, CI
import pomagma.reducer.io as io
import pytest

EXAMPLES_BY_TYPE = {
    'unit': {
        'ok': [(I, None)],
        'encode_error': [True, False, 0, 1, 2, [None], [True]],
        'decode_error': [K, B, C, APP(C, B)],
    },
    'bool': {
        'ok': [(K, True), (KI, False)],
        'encode_error': [None, 0, 1, 2, [None], [True]],
        'decode_error': [I, B, C, APP(C, B)],
    },
    'num': {
        'ok': [(K, 0)],
        'encode_error': [None, False, True, [0], [True]],
    },
    ('maybe', 'bool'): {
        'ok': [
            (K, None),
            (APP(K, APP(CI, K)), (True,)),
            (APP(K, APP(CI, KI)), (False,)),
        ],
        'encode_error': [True, False, 0, 1, 2, (), 'asdf'],
        'decode_error': [I],
    },
    ('list', 'bool'): {
        'ok': [
            (K, []),
        ],
        'encode_error': [None, True, False, 0, 1, 2, (), 'asdf'],
        'decode_error': [I],
    },
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
