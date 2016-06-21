from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, APP, JOIN
from pomagma.reducer.code import is_app, is_join
from pomagma.util import TODO

PROTOCOL_VERSION = '0.0.1'  # Subject to backwards-incompatible change.


# ----------------------------------------------------------------------------
# Packed varints.

ARGC_BITS = 3  # Up to 3 args and 16 atoms before varint overflow.
HEAD_BITS = 8 - ARGC_BITS

HEAD_MASK = 0xff >> ARGC_BITS
ARGC_MASK = 0xff ^ HEAD_MASK

# HEAD and ARGC are varint coded, after the initial bits.
HEAD_OVERFLOW = 1 << (HEAD_BITS - 1)
ARGC_OVERFLOW = 1 << (ARGC_BITS - 1)
BYTE_OVERFLOW = 1 << (8 - 1)


def _pack_bytes(head, argc):
    if head >= HEAD_OVERFLOW:
        TODO('support varint encoding of head')
    if argc >= ARGC_OVERFLOW:
        TODO('support varint encoding of argc')
    yield chr(head | (argc << HEAD_BITS))


def _unpack_bytes(source):
    byte = ord(next(source))
    head = byte & HEAD_MASK
    argc = (byte & ARGC_MASK) >> HEAD_BITS
    if head >= HEAD_OVERFLOW:
        raise TODO('support varint decoding of head')
    if argc >= ARGC_OVERFLOW:
        raise TODO('support varint decoding of argc')
    return head, argc


# ----------------------------------------------------------------------------
# Coding of atoms.

J = intern('J')  # Simulates JOIN.

INT_TO_ATOM = [TOP, BOT, I, K, B, C, S, J]
ATOM_TO_INT = {k: v for v, k in enumerate(INT_TO_ATOM)}


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
        head = J
    try:
        head = ATOM_TO_INT[head]
    except KeyError:
        raise ValueError('Failed to serialize code: {}'.format(code))
    argc = len(args)
    for byte in _pack_bytes(head, argc):
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
    head, argc = _unpack_bytes(bytes_)
    try:
        head = INT_TO_ATOM[head]
    except IndexError:
        raise ValueError('Unrecognized symbol: {}'.format(head))
    if head is J:
        if argc < 2:
            TODO('support J with fewer than 2 args')
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
