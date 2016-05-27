from pomagma.examples.testing import ADDRESS
from pomagma.examples.testing import SKJA
from pomagma.examples.testing import WORLD
from pomagma.examples.testing import serve
import pomagma.examples.solve


def _test_define(name, theory):
    with serve(theory):
        pomagma.examples.solve.define(name, address=ADDRESS)


def test_define():
    for name in pomagma.examples.solve.theories:
        if name.endswith('_test'):
            yield _test_define, name, WORLD
    for name in pomagma.examples.solve.theories:
        yield _test_define, name, SKJA


def test_rs_pairs():
    with serve(SKJA):
        pomagma.examples.solve.rs_pairs(address=ADDRESS)
