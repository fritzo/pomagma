from pomagma.reducer import __main__ as main
from pomagma.util.testing import for_each

EXAMPLES = [
    ('I', 0),
    ('K', 0),
    ('B', 0),
    ('C', 0),
    ('S', 0),
    ('APP I I', 0),
    ('APP I', 1),
    ('APP I I I', 1),
]


@for_each(EXAMPLES)
def test_reduce_does_not_crash(code, error_count):
    assert main.reduce(code) == error_count
