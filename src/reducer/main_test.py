from pomagma.reducer import __main__ as main
from pomagma.util.testing import for_each


@for_each([
    ('I', 0),
    ('K', 0),
    ('B', 0),
    ('C', 0),
    ('S', 0),
    ('APP I I', 0),
    ('APP I', 1),
    ('APP I I I', 1),
])
def test_reduce_cpp_does_not_crash(code, error_count):
    assert main.reduce_cpp(code) == error_count
