from StringIO import StringIO
from pomagma.reducer.code import I, K, B, C, S, APP
from pomagma.reducer.serial import dump
from pomagma.reducer.serial import load
from pomagma.util.testing import for_each


@for_each([
    I,
    K,
    B,
    C,
    S,
    APP(K, I),
    APP(APP(B, C), S),
])
def test_serialize_deserialize(code):
    f_out = StringIO()
    dump(code, f_out)
    serialized = f_out.getvalue()
    f_out.close()

    f_in = StringIO(serialized)
    actual = load(f_in)
    f_in.close()

    assert actual == code
