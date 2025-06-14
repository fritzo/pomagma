from pomagma.compiler import parser
from pomagma.compiler.util import find_theories
from pomagma.util.testing import for_each


@for_each(find_theories())
def test_parse_theory_file(filename):
    parser.parse_theory_file(filename)


@for_each(find_theories())
def test_parse_theory_string(filename):
    with open(filename) as f:
        string = f.read()
    parser.parse_theory_string(string)
