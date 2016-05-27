from pomagma.reducer import __main__ as main
import pytest

EXAMPLES = [
    ('I', 0),
    ('K', 0),
    ('B', 0),
    ('C', 0),
    ('S', 0),
    pytest.mark.xfail(('APP I I', 0)),
    ('APP I', 1),
    pytest.mark.xfail(('APP I I I', 1)),
]


@pytest.mark.parametrize('code,error_count', EXAMPLES)
def test_reduce_does_not_crash(code, error_count):
    assert main.reduce(code) == error_count
