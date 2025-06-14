import os

from pomagma.compiler import parser, sequents
from pomagma.compiler.sugar import desugar_theory
from pomagma.compiler.util import find_theories
from pomagma.util.testing import for_each

RULE_SETS = {
    os.path.basename(f): desugar_theory(parser.parse_theory_file(f))["rules"]
    for f in find_theories()
}


@for_each(RULE_SETS)
def test_contrapositives(name):
    print("# contrapositives")
    print()
    for rule in RULE_SETS[name]:
        print(rule.ascii())
        print()
        if len(rule.succedents) != 1:
            print("    TODO")
            print()
            continue
        for seq in sequents.get_contrapositives(rule):
            print(seq.ascii(indent=4))
            print()


@for_each(RULE_SETS)
def test_get_atomic(name):
    print("# get_atomic")
    print()
    for rule in RULE_SETS[name]:
        print(rule.ascii())
        print()
        if len(rule.succedents) != 1:
            print("    TODO")
            print()
            continue
        for seq in sequents.get_atomic(rule):
            print(seq.ascii(indent=4))
            print()


@for_each(RULE_SETS)
def test_normalize(name):
    print("# normalized")
    print()
    for rule in RULE_SETS[name]:
        print(rule.ascii())
        print()
        if len(rule.succedents) != 1:
            print("    TODO")
            print()
            continue
        for seq in sequents.normalize(rule):
            print(seq.ascii(indent=4))
            print()
            sequents.assert_normal(seq)
