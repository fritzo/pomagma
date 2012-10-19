from pomagma.compiler import parser, expressions
import glob


def test_parse_rule():
    for filename in glob.glob('../theory/*.rules'):
        yield parser.parse_rules, filename


def test_parse_facts():
    for filename in glob.glob('../theory/*.facts'):
        yield parser.parse_facts, filename
