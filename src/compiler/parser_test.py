from pomagma.compiler import parser
from pomagma.compiler.util import find_facts, find_rules


def test_parse_rule():
    for filename in find_rules():
        yield parser.parse_rules, filename


def test_parse_facts():
    for filename in find_facts():
        yield parser.parse_facts, filename
