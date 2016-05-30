'''Translators between SKJ/H* codes and json.'''

from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer import lib
import unification


# ----------------------------------------------------------------------------
# Errors

def _contains(code, atom):
    if code is atom:
        return True
    elif isinstance(code, tuple):
        return any(_contains(arg, atom) for arg in code[1:])
    else:
        return False


def check_for_errors(code):
    if _contains(code, lib.error):
        raise RuntimeError(code)
    if _contains(code, lib.undefined):
        raise NotImplementedError(code)


# ----------------------------------------------------------------------------
# Unit

def encode_unit(value):
    if value is not None:
        raise TypeError(value)
    return lib.void


def decode_unit(code):
    """Decode unit to None, or raise an exception."""
    if code is lib.void:
        return None
    else:
        raise TypeError(code)


# ----------------------------------------------------------------------------
# Bool

def encode_bool(value):
    if not isinstance(value, bool):
        raise TypeError(value)
    return lib.true if value else lib.false


def decode_bool(code):
    """Decode bool to {True, False} or raise an exception."""
    if code is lib.true:
        return True
    elif code is lib.false:
        return False
    else:
        raise TypeError(code)


# ----------------------------------------------------------------------------
# Maybe


@memoize_arg
def encode_maybe(encode_item):

    def encode(value):
        if value is None:
            return lib.none
        if isinstance(value, tuple) and len(value) == 1:
            return lib.some(encode_item(value[0]))
        else:
            raise TypeError(value)

    return encode


@memoize_arg
def decode_maybe(decode_item):
    item_var = unification.var('item')
    some_pattern = lib.some(item_var)

    def decode(code):
        if code is lib.none:
            return None
        match = unification.unify(some_pattern, code)
        if not match:
            raise TypeError(code)
        return (decode_item(match[item_var]),)

    return decode


# ----------------------------------------------------------------------------
# Products

@memoize_args
def encode_prod(encode_fst, encode_snd):

    def encode(value):
        if not (isinstance(value, tuple) and len(value) == 2):
            raise TypeError(value)
        code_fst = encode_fst(value[0])
        code_snd = encode_snd(value[1])
        return lib.pair(code_fst, code_snd)

    return encode


@memoize_args
def decode_prod(decode_fst, decode_snd):
    x = unification.var('x')
    y = unification.var('y')
    pair_pattern = lib.pair(x, y)

    def decode(code):
        match = unification.unify(pair_pattern, code)
        if not match:
            raise TypeError(code)
        x_value = decode_fst(match[x])
        y_value = decode_snd(match[y])
        return (x_value, y_value)

    return decode


# ----------------------------------------------------------------------------
# Sums

@memoize_args
def encode_sum(encode_inl, encode_inr):

    def encode(value):
        if not (isinstance(value, tuple) and len(value) == 2 and
                isinstance(value[0], bool)):
            raise TypeError(value)
        if value[0]:
            return lib.inl(encode_inl(value[1]))
        else:
            return lib.inr(encode_inr(value[1]))

    return encode


@memoize_args
def decode_sum(decode_inl, decode_inr):
    x = unification.var('x')
    inl_pattern = lib.inl(x)
    inr_pattern = lib.inr(x)

    def decode(code):
        match = unification.unify(inl_pattern, code)
        if match:
            return (True, decode_inl(match[x]))
        match = unification.unify(inr_pattern, code)
        if match:
            return (False, decode_inr(match[x]))
        raise TypeError(code)

    return decode


# ----------------------------------------------------------------------------
# Numerals as Y Maybe

def encode_num(num):
    if not isinstance(num, int) or isinstance(num, bool) or not num >= 0:
        raise TypeError(num)
    result = lib.zero
    for i in xrange(num):
        result = lib.succ(result)
    return result


_pred_var = unification.var('pred')
_succ_pattern = lib.succ(_pred_var)


def decode_num(code):
    result = 0
    while True:
        if code is lib.zero:
            return result
        match = unification.unify(_succ_pattern, code)
        if not match:
            raise TypeError(code)
        result += 1
        code = match[_pred_var]


# ----------------------------------------------------------------------------
# Finite homogeneous lists

@memoize_arg
def encode_list(encode_item):

    def encode(values):
        if not isinstance(values, list):
            raise TypeError(values)
        code = lib.nil
        for value in reversed(values):
            code = lib.cons(encode_item(value), code)
        return code

    return encode


@memoize_arg
def decode_list(decode_item):
    head = unification.var('head')
    tail = unification.var('tail')
    cons_pattern = lib.cons(head, tail)

    def decode(code):
        result = []
        while code is not lib.nil:
            match = unification.unify(cons_pattern, code)
            if not match:
                raise TypeError(code)
            result.append(decode_item(match[head]))
            code = match[tail]
        return result

    return decode


# ----------------------------------------------------------------------------
# Generic

def decoder(tp):
    if not isinstance(tp, tuple):
        if tp == 'unit':
            return decode_unit
        if tp == 'bool':
            return decode_bool
        if tp == 'num':
            return decode_num
    elif len(tp) == 2:
        if tp[0] == 'maybe':
            return decode_maybe(decoder(tp[1]))
        if tp[0] == 'list':
            return decode_list(decoder(tp[1]))
    elif len(tp) == 3:
        if tp[0] == 'prod':
            return decode_prod(decoder(tp[1]), decoder(tp[2]))
        if tp[0] == 'sum':
            return decode_sum(decoder(tp[1]), decoder(tp[2]))
    raise ValueError(tp)


def encoder(tp):
    if not isinstance(tp, tuple):
        if tp == 'unit':
            return encode_unit
        if tp == 'bool':
            return encode_bool
        if tp == 'num':
            return encode_num
    elif len(tp) == 2:
        if tp[0] == 'maybe':
            return encode_maybe(encoder(tp[1]))
        if tp[0] == 'list':
            return encode_list(encoder(tp[1]))
    elif len(tp) == 3:
        if tp[0] == 'prod':
            return encode_prod(encoder(tp[1]), encoder(tp[2]))
        if tp[0] == 'sum':
            return encode_sum(encoder(tp[1]), encoder(tp[2]))
    raise ValueError(tp)
