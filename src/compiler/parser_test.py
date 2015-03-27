from pomagma.compiler import parser
from pomagma.compiler.util import find_theories


def test_parse_theory():
    for filename in find_theories():
        yield parser.parse_theory, filename
