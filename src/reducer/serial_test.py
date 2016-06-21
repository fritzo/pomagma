from StringIO import StringIO
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, APP, JOIN
from pomagma.reducer.serial import dump
from pomagma.reducer.serial import load
from pomagma.util.testing import for_each


@for_each([
    TOP,
    BOT,
    I,
    K,
    B,
    C,
    S,
    APP(K, I),
    APP(APP(B, C), S),
    APP(APP(APP(S, K), I), B),
    JOIN(I, K),
    JOIN(APP(K, I), K),
    APP(JOIN(APP(K, I), K), I),
])
def test_serialize_deserialize(code):
    f_out = StringIO()
    dump(code, f_out)
    serialized = f_out.getvalue()
    print(' '.join('{:02x}'.format(ord(c)) for c in serialized))
    f_out.close()

    f_in = StringIO(serialized)
    actual = load(f_in)
    f_in.close()

    assert actual == code
