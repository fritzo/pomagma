import os
from pomagma.compiler import sequents
from pomagma.compiler import parser
from pomagma.compiler.util import find_theories
from pomagma.compiler.sugar import desugar_theory

RULE_SETS = {
    os.path.basename(f): desugar_theory(parser.parse_theory_file(f))['rules']
    for f in find_theories()
}


def _test_contrapositives(name):
    print '# contrapositives'
    print
    for rule in RULE_SETS[name]:
        print rule.ascii()
        print
        if len(rule.succedents) != 1:
            print '    TODO'
            print
            continue
        for seq in sequents.get_contrapositives(rule):
            print seq.ascii(indent=4)
            print


def test_contrapositives():
    for name in RULE_SETS:
        yield _test_contrapositives, name


def _test_get_atomic(name):
    print '# get_atomic'
    print
    for rule in RULE_SETS[name]:
        print rule.ascii()
        print
        if len(rule.succedents) != 1:
            print '    TODO'
            print
            continue
        for seq in sequents.get_atomic(rule):
            print seq.ascii(indent=4)
            print


def test_get_atomic():
    for name in RULE_SETS:
        yield _test_get_atomic, name


def _test_normalize(name):
    print '# normalized'
    print
    for rule in RULE_SETS[name]:
        print rule.ascii()
        print
        if len(rule.succedents) != 1:
            print '    TODO'
            print
            continue
        for seq in sequents.normalize(rule):
            print seq.ascii(indent=4)
            print
            sequents.assert_normal(seq)


def test_normalize():
    for name in RULE_SETS:
        yield _test_normalize, name
