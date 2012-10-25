import os
import glob
from pomagma.compiler import run


def _test_close_rules(filename):
    outfile = 'temp.derived.facts'
    run.close_rules(filename, outfile)
    os.remove(outfile)


def test_close_rules():
    for filename in glob.glob('../theory/*.rules'):
        yield _test_close_rules, filename
