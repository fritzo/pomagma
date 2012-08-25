from pomagma import parser, expressions
import glob


def test_parse():
    for filename in glob.glob('*.rules'):
        yield parser.parse, filename
