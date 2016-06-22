from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, _JOIN, APP, JOIN
from pomagma.reducer.code import is_app, is_join

__all__ = ['dump', 'load']

PROTOCOL_VERSION = '0.0.2'  # Subject to backwards-incompatible change.


# ----------------------------------------------------------------------------
# Packed varints.
# These use an LZ4-style packing for the first few bits and protobuf-style
# packing for all additional bytes.

ARGC_BITS = 3  # Up to 6 args and 31 atoms before varint overflow.
HEAD_BITS = 8 - ARGC_BITS
VARINT_BITS = 7

HEAD_MASK = 0xff >> (8 - HEAD_BITS)
ARGC_MASK = 0xff >> (8 - ARGC_BITS)
VARINT_MASK = 0xff >> (8 - VARINT_BITS)
OVERFLOW_MASK = 0xff ^ VARINT_MASK


def pack_varint(count):
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
    yield chr(min(head, HEAD_MASK) ^ (min(argc, ARGC_MASK) << HEAD_BITS))
    if head >= HEAD_MASK:
        for c in pack_varint(head - HEAD_MASK):
            yield c
    if argc >= ARGC_MASK:
        for c in pack_varint(argc - ARGC_MASK):
            yield c


def unpack_head_argc(source):
    byte = ord(next(source))
    head = byte & HEAD_MASK
    argc = byte >> HEAD_BITS
    if head == HEAD_MASK:
        head += unpack_varint(source)
    if argc == ARGC_MASK:
        argc += unpack_varint(source)
    return head, argc


# ----------------------------------------------------------------------------
# Coding of atoms.

INT_TO_SYMB = [TOP, BOT, I, K, B, C, S, _JOIN]
SYMB_TO_INT = {k: v for v, k in enumerate(INT_TO_SYMB)}


# ----------------------------------------------------------------------------
# Dumping and loading.

def dump(code, f):
    head = code
    args = []
    while is_app(head):
        args.append(head[2])
        head = head[1]
    if is_join(head):
        args.append(head[2])
        args.append(head[1])
        head = _JOIN
    try:
        head = SYMB_TO_INT[head]
    except KeyError:
        raise ValueError('Failed to serialize code: {}'.format(code))
    argc = len(args)
    for byte in pack_head_argc(head, argc):
        f.write(byte)
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
    if head is _JOIN:
        if argc < 2:
            raise ValueError('JOIN requires at least two args')
        argc -= 2
        x = _load_from(bytes_)
        y = _load_from(bytes_)
        head = JOIN(x, y)
    for _ in xrange(argc):
        arg = _load_from(bytes_)
        head = APP(head, arg)
    return head


def load(f):
    bytes_ = _iter_bytes(f)
    return _load_from(bytes_)
