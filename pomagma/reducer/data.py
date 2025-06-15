"""Translators between terms and a json-like fragment of python.

encode : python -> Term
decode : Term -> python
"""

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer import lib, pattern
from pomagma.reducer.bohm import reduce
from pomagma.reducer.sugar import app
from pomagma.reducer.syntax import NVAR, sexpr_print
from pomagma.util import TODO

pretty = sexpr_print


# ----------------------------------------------------------------------------
# Errors


def _contains(term, atom):
    if term is atom:
        return True
    if isinstance(term, tuple):
        return any(_contains(arg, atom) for arg in term[1:])
    return False


def check_for_errors(term):
    if _contains(term, lib.error):
        raise RuntimeError(pretty(term))
    if _contains(term, lib.undefined):
        raise NotImplementedError(pretty(term))


# ----------------------------------------------------------------------------
# Unit


def encode_unit(value):
    if value is not None:
        raise TypeError(value)
    return lib.ok


def decode_unit(term):
    """Decode unit to None, or raise an exception."""
    if term is lib.ok:
        return
    raise TypeError(pretty(term))


# ----------------------------------------------------------------------------
# Bool


def encode_bool(value):
    if not isinstance(value, bool):
        raise TypeError(value)
    return lib.true if value else lib.false


def decode_bool(term):
    """Decode bool to {True, False} or raise an exception."""
    if term is lib.true:
        return True
    if term is lib.false:
        return False
    raise TypeError(pretty(term))


# ----------------------------------------------------------------------------
# Byte

_encode_byte = {chr(k): v for k, v in list(lib.byte_table.items())}
_decode_byte = {v: chr(k) for k, v in list(lib.byte_table.items())}


@memoize_arg
def encode_byte(byte):
    if not isinstance(byte, bytes) or len(byte) != 1:
        raise TypeError(byte)
    try:
        # Convert bytes to string for dictionary lookup
        char = byte.decode("latin-1")
        return _encode_byte[char]
    except KeyError:
        raise TypeError(byte)


@memoize_arg
def decode_byte(term):
    try:
        # _decode_byte returns a string, convert to bytes
        char = _decode_byte[term]
        return char.encode("latin-1")
    except KeyError:
        raise TypeError(pretty(term))


# ----------------------------------------------------------------------------
# Maybe


@memoize_arg
def encode_maybe(encode_item):
    """Encode either None to lib.none or (v,) to lib.some(encode_item(v))."""

    def encode(value):
        if value is None:
            return lib.none
        if isinstance(value, tuple) and len(value) == 1:
            return lib.some(encode_item(value[0]))
        raise TypeError(value)

    return encode


@memoize_arg
def decode_maybe(decode_item):
    """Decode to either None or (decode_item(...),)."""
    item_var = NVAR("item")
    some_pattern = lib.some(item_var)

    def decode(term):
        if term is lib.none:
            return None
        match = pattern.match(some_pattern, term)
        if match is None:
            raise TypeError(pretty(term))
        return (decode_item(match[item_var]),)

    return decode


# ----------------------------------------------------------------------------
# Products


@memoize_args
def encode_prod(encode_fst, encode_snd):
    def encode(value):
        if not (isinstance(value, tuple) and len(value) == 2):
            raise TypeError(value)
        term_fst = encode_fst(value[0])
        term_snd = encode_snd(value[1])
        return lib.pair(term_fst, term_snd)

    return encode


@memoize_args
def decode_prod(decode_fst, decode_snd):
    x = NVAR("x")
    y = NVAR("y")
    pair_pattern = lib.pair(x, y)

    def decode(term):
        match = pattern.match(pair_pattern, term)
        if match is None:
            raise TypeError(pretty(term))
        x_value = decode_fst(match[x])
        y_value = decode_snd(match[y])
        return (x_value, y_value)

    return decode


# ----------------------------------------------------------------------------
# Sums


@memoize_args
def encode_sum(encode_inl, encode_inr):
    def encode(value):
        if not (
            isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], bool)
        ):
            raise TypeError(value)
        if value[0]:
            return lib.inl(encode_inl(value[1]))
        return lib.inr(encode_inr(value[1]))

    return encode


@memoize_args
def decode_sum(decode_inl, decode_inr):
    x = NVAR("x")
    inl_pattern = lib.inl(x)
    inr_pattern = lib.inr(x)

    def decode(term):
        match = pattern.match(inl_pattern, term)
        if match:
            return (True, decode_inl(match[x]))
        match = pattern.match(inr_pattern, term)
        if match:
            return (False, decode_inr(match[x]))
        raise TypeError(pretty(term))

    return decode


# ----------------------------------------------------------------------------
# Numerals as Y Maybe


def encode_num(num):
    if not isinstance(num, int) or isinstance(num, bool) or not num >= 0:
        raise TypeError(num)
    result = lib.zero
    for i in range(num):
        result = lib.succ(result)
    return result


_pred_var = NVAR("pred")
_succ_pattern = lib.succ(_pred_var)


def decode_num(term):
    result = 0
    while True:
        if term is lib.zero:
            return result
        match = pattern.match(_succ_pattern, term)
        if match is None:
            raise TypeError(pretty(term))
        result += 1
        term = match[_pred_var]


# ----------------------------------------------------------------------------
# Finite homogeneous lists


@memoize_arg
def encode_list(encode_item):
    def encode(values):
        if not isinstance(values, list):
            raise TypeError(values)
        term = lib.nil
        for value in reversed(values):
            term = lib.cons(encode_item(value), term)
        return term

    return encode


@memoize_arg
def decode_list(decode_item):
    head = NVAR("head")
    tail = NVAR("tail")
    cons_pattern = lib.cons(head, tail)

    def decode(term):
        result = []
        while term is not lib.nil:
            match = pattern.match(cons_pattern, term)
            if match is None:
                raise TypeError(pretty(term))
            result.append(decode_item(match[head]))
            term = match[tail]
        return result

    return decode


# ----------------------------------------------------------------------------
# Bytes


def encode_bytes(value):
    if not isinstance(value, bytes):
        raise TypeError(value)
    # In Python 3, list(bytes) returns integers, so convert each to single-byte bytes
    byte_list = [bytes([b]) for b in value]
    return encode_list(encode_byte)(byte_list)


def decode_bytes(term):
    byte_list = decode_list(decode_byte)(term)
    return b"".join(byte_list)


# ----------------------------------------------------------------------------
# Functions


@memoize_arg
def encode_fun(decode_args, encode_result):
    def encode(py_fun):
        TODO("encode python function as a combinator")

    return encode


@memoize_arg
def decode_fun(encode_args, decode_result):
    def decode(un_fun):
        def py_fun(*py_args):
            assert len(py_args) == len(encode_args)
            un_args = tuple(e(a) for (e, a) in zip(encode_args, py_args))
            un_result = reduce(app(un_fun, *un_args))
            return decode_result(un_result)

        return py_fun

    return decode


# ----------------------------------------------------------------------------
# Generic


def decoder(tp):
    if not isinstance(tp, tuple):
        if tp == "unit":
            return decode_unit
        if tp == "bool":
            return decode_bool
        if tp == "byte":
            return decode_byte
        if tp == "num":
            return decode_num
        if tp == "bytes":
            return decode_bytes
    elif len(tp) == 2:
        if tp[0] == "maybe":
            return decode_maybe(decoder(tp[1]))
        if tp[0] == "list":
            return decode_list(decoder(tp[1]))
        if tp[0] == "fun":
            encode_args = list(map(encoder, tp[1]))
            decode_result = decoder(tp[2])
            return decode_fun(encode_args, decode_result)
    elif len(tp) == 3:
        if tp[0] == "prod":
            return decode_prod(decoder(tp[1]), decoder(tp[2]))
        if tp[0] == "sum":
            return decode_sum(decoder(tp[1]), decoder(tp[2]))
    raise ValueError(tp)


def encoder(tp):
    if not isinstance(tp, tuple):
        if tp == "unit":
            return encode_unit
        if tp == "bool":
            return encode_bool
        if tp == "byte":
            return encode_byte
        if tp == "num":
            return encode_num
        if tp == "bytes":
            return encode_bytes
    elif len(tp) == 2:
        if tp[0] == "maybe":
            return encode_maybe(encoder(tp[1]))
        if tp[0] == "list":
            return encode_list(encoder(tp[1]))
        if tp[0] == "fun":
            decode_args = list(map(decoder, tp[1]))
            encode_result = encoder(tp[2])
            return encode_fun(decode_args, encode_result)
    elif len(tp) == 3:
        if tp[0] == "prod":
            return encode_prod(encoder(tp[1]), encoder(tp[2]))
        if tp[0] == "sum":
            return encode_sum(encoder(tp[1]), encoder(tp[2]))
    raise ValueError(tp)
