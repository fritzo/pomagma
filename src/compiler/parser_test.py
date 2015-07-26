from pomagma.compiler import parser
from pomagma.compiler.util import find_theories


def test_parse_theory_file():
    for filename in find_theories():
        yield parser.parse_theory_file, filename


def _test_parse_theory_string(filename):
    with open(filename) as f:
        parser.parse_theory_string(f.read())


def test_parse_theory_string():
    for filename in find_theories():
        yield _test_parse_theory_string, filename
