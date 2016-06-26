"""Binary serialization format for code.

The format is roughly a byte-oriented packed tree format that allows embedded
raw binary length-delimited data.

Message format in bytes:

    [3|--5--]               argc_lo : 3bits | head_lo : 5bits
    [1|--7--]...[1|--7--]   argc_overflow : varint if argc_lo == 7
    [1|--7--]...[1|--7--]   head_overflow : varint if head_lo == 31
    [---8---]...[---8---]   raw bytes : (argc if head == 0 else 0) bytes
    ...                     args : (argc if head != 0 else 0) messages

Varint format in bytes:

    [1|--7--]               overflow : bit | value : 7bits
    ...                     varint if overflow == 1

1.  There are three types of bytes
    a.  symbol bytes, that pack 3+5 bits to represent (3-bits) the number of
        arguments in an S-Expression, and (5-bits) a numerical code for the
        head atom of this S-Expression. All S-Expressions in this language
        begin with an atom.
    b.  varint bytes for various counts, including: arg counts beyond the 3-bit
        limit, atom ids beyond the 5-bit limit, and raw bytes length delimiters
        beyond the 3-bit limit.
    c.  raw bytes.
2.  The first byte of a sequence is 3 high + 5 low bits broken into 'argc' and
    'head', respectively.
    If 'argc' reaches its 3-bit limit (at 7), a varint is read from the
    following bytes and added to the value 7.
    Then if 'head' reaches its 5-bit limit (at 31), a varint is read from the
    next following bytes and added to the value 31.
3.  If 'head' is 0, this message is raw bytes, and 'argc' denotes the number
    of bytes to read from the remaining stream.
4.  If 'head' is nonzero, this message is an APP expression with head atom
    'head', i.e. APP(...APP(head, args[0])..., args[argc-1]). 'argc' many
    additional messages are read off the stream and added to the APP tree.
5.  Each 'head' symbol may override the semantics of the first few args, so
    e.g. whereas normally [S K I] -> APP(APP(S, K), I), because S is normal,
    [VAR x I] -> APP(VAR(x), I), since VAR overrides one argument
6.  Varints are coded as: 7 lower bits denoting part of a number in 0,1,2,...,
    followed by 1 bit that is 1 iff more bytes are needed (a la protobuf).
    The end result of a varint is all of the 7-bit pieces concatenated
    together, excluding the overflow bit from each byte.
    Note that in both argc and head id numbers, the value of this varint is
    added to the 3- or 5-bit initial part, not bitwise concatenated.
    This is thus a hybrid coding combining techniques used in LZ4 (adding)
    and protocol buffers (bitwise concatenating).

"""

__all__ = ['dump', 'load', 'PROTOCOL_VERSION']

from cStringIO import StringIO
from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import VAR, APP, JOIN, FUN, LET
from pomagma.reducer.code import _VAR, _JOIN, _FUN, _LET
from pomagma.reducer.code import is_var, is_app, is_join, is_fun, is_let

PROTOCOL_VERSION = '0.0.4'  # Semver compliant.

# ----------------------------------------------------------------------------
# Packed varints.
# These use an LZ4-style packing for the first few bits and protobuf-style
# packing for all additional bytes.

ARGC_BITS = 3  # Up to 6 args and 1+30 atoms before varint overflow.
HEAD_BITS = 8 - ARGC_BITS
VARINT_BITS = 7

HEAD_MASK = 0xff >> (8 - HEAD_BITS)
ARGC_MASK = 0xff >> (8 - ARGC_BITS)
VARINT_MASK = 0xff >> (8 - VARINT_BITS)
OVERFLOW_MASK = 0xff ^ VARINT_MASK

INT_TYPES = (int, long)


def pack_varint(count):
    assert isinstance(count, INT_TYPES)
    byte = count & VARINT_MASK
    count >>= VARINT_BITS
    while count:
        byte ^= OVERFLOW_MASK
        yield chr(byte)
        byte = count & VARINT_MASK
        count >>= VARINT_BITS
    yield chr(byte)


def unpack_varint(source):
    offset = 0
    byte = ord(next(source))
    result = byte & VARINT_MASK
    while byte & OVERFLOW_MASK:
        offset += VARINT_BITS
        byte = ord(next(source))
        result ^= (byte & VARINT_MASK) << offset
    return result


def pack_head_argc(head, argc):
    assert isinstance(head, INT_TYPES)
    assert isinstance(argc, INT_TYPES)
    yield chr(min(head, HEAD_MASK) ^ (min(argc, ARGC_MASK) << HEAD_BITS))
    if argc >= ARGC_MASK:
        for c in pack_varint(argc - ARGC_MASK):
            yield c
    if head >= HEAD_MASK:
        for c in pack_varint(head - HEAD_MASK):
            yield c


def unpack_head_argc(source):
    byte = ord(next(source))
    head = byte & HEAD_MASK
    argc = byte >> HEAD_BITS
    if argc == ARGC_MASK:
        argc += unpack_varint(source)
    if head == HEAD_MASK:
        head += unpack_varint(source)
    return head, argc


# ----------------------------------------------------------------------------
# Coding of atoms.

RAW_BYTES = object()

INT_TO_SYMB = [
    RAW_BYTES,
    HOLE, TOP, BOT, I, K, B, C, S,
    _VAR, _JOIN, _FUN, _LET,
]
SYMB_TO_INT = {k: v for v, k in enumerate(INT_TO_SYMB) if k is not RAW_BYTES}


# ----------------------------------------------------------------------------
# Dumping and loading.

def _dump_raw_bytes(raw_bytes, f):
    assert isinstance(raw_bytes, bytes)
    _dump_head_argc(0, len(raw_bytes), f)
    f.write(raw_bytes)


def _load_raw_bytes(byte_count, bytes_):
    f = StringIO()
    for _ in xrange(byte_count):
        f.write(next(bytes_))
    return f.getvalue()


def _dump_head_argc(head, argc, f):
    for byte in pack_head_argc(head, argc):
        f.write(byte)


def dump(code, f):
    head = code
    args = []
    while is_app(head):
        args.append(head[2])
        head = head[1]
    if is_var(head):
        _dump_head_argc(SYMB_TO_INT[_VAR], 1 + len(args), f)
        _dump_raw_bytes(head[1], f)
    elif is_join(head):
        args.append(head[2])
        args.append(head[1])
        _dump_head_argc(SYMB_TO_INT[_JOIN], len(args), f)
    elif is_fun(head):
        args.append(head[2])
        args.append(head[1])
        _dump_head_argc(SYMB_TO_INT[_FUN], len(args), f)
    elif is_let(head):
        args.append(head[3])
        args.append(head[2])
        args.append(head[1])
        _dump_head_argc(SYMB_TO_INT[_LET], len(args), f)
    else:
        try:
            head = SYMB_TO_INT[head]
        except KeyError:
            raise ValueError('Failed to serialize code: {}'.format(code))
        _dump_head_argc(head, len(args), f)
    for arg in reversed(args):
        dump(arg, f)


def _iter_bytes(f, buffsize=8192):
    while True:
        buff = f.read(buffsize)
        if not buff:
            break
        for b in buff:
            yield b


def _load_from(bytes_):
    head, argc = unpack_head_argc(bytes_)
    try:
        head = INT_TO_SYMB[head]
    except IndexError:
        raise ValueError('Unrecognized symbol: {}'.format(head))
    if head is RAW_BYTES:
        return _load_raw_bytes(argc, bytes_)
    if head is _VAR:
        if argc < 1:
            raise ValueError('VAR requires at least one arg')
        argc -= 1
        name = _load_from(bytes_)
        head = VAR(name)
    elif head is _JOIN:
        if argc < 2:
            raise ValueError('JOIN requires at least two args')
        argc -= 2
        x = _load_from(bytes_)
        y = _load_from(bytes_)
        head = JOIN(x, y)
    elif head is _FUN:
        if argc < 2:
            raise ValueError('FUN requires at least two args')
        argc -= 2
        var = _load_from(bytes_)
        body = _load_from(bytes_)
        head = FUN(var, body)
    elif head is _LET:
        if argc < 3:
            raise ValueError('LET requires at least three args')
        argc -= 3
        var = _load_from(bytes_)
        defn = _load_from(bytes_)
        body = _load_from(bytes_)
        head = LET(var, defn, body)
    for _ in xrange(argc):
        arg = _load_from(bytes_)
        head = APP(head, arg)
    print('DEBUG {}'.format(head))
    return head


def load(f):
    bytes_ = _iter_bytes(f)
    return _load_from(bytes_)
