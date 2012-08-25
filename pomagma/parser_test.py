from pomagma import parser
import glob


def test_parse():
    for filename in glob.glob('*.rules'):
        yield parser.parse, filename
