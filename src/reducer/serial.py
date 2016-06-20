from pomagma.reducer.code import I, K, B, C, S, APP, is_app

ARGC_BITS = 2
MAX_ARGC = (1 << ARGC_BITS) - 2
ATOM_TO_INT = {
    I: 0x1 << ARGC_BITS,
    K: 0x2 << ARGC_BITS,
    B: 0x3 << ARGC_BITS,
    C: 0x4 << ARGC_BITS,
    S: 0x5 << ARGC_BITS,
}
INT_TO_ATOM = {v: k for k, v in ATOM_TO_INT.iteritems()}


def dump(code, f):
    head = code
    args = []
    while is_app(head):
        args.append(head[2])
        head = head[1]
    byte = len(args)
    if byte > MAX_ARGC:
        raise NotImplementedError(
            'argc > {} is not implemented'.format(MAX_ARGC))
    try:
        byte |= ATOM_TO_INT[head]
    except KeyError:
        raise ValueError('Failed to serialize code: {}'.format(code))
    f.write(chr(byte))
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
    byte = ord(next(bytes_))
    argc = byte & 0x3
    head = byte & 0xFC
    try:
        head = INT_TO_ATOM[head]
    except KeyError:
        raise ValueError('Failed to deserialize byte: {:x}'.format(byte))
    for _ in xrange(argc):
        arg = _load_from(bytes_)
        head = APP(head, arg)
    return head


def load(f):
    bytes_ = _iter_bytes(f)
    return _load_from(bytes_)
