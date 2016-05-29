from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, APP, JOIN
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
import pytest

EXAMPLES = [
    ('I', I),
    ('K', K),
    ('B', B),
    ('C', C),
    ('S', S),
    ('TOP', TOP),
    ('BOT', BOT),
    ('APP I K', APP(I, K)),
    ('JOIN K APP K I', JOIN(K, APP(K, I))),
    ('APP APP I K JOIN B C', APP(APP(I, K), JOIN(B, C))),
]


@pytest.mark.parametrize('string, code', EXAMPLES)
def test_parse(string, code):
    actual_string = serialize(code)
    assert actual_string == string


@pytest.mark.parametrize('string, code', EXAMPLES)
def test_serialize(string, code):
    actual_code = parse(string)
    assert actual_code == code
