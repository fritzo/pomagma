from pomagma.compiler import parser, expressions
import glob


def test_parse():
    for filename in glob.glob('../theory/*.rules'):
        yield parser.parse, filename
