from pomagma.examples.testing import ADDRESS
from pomagma.examples.testing import SKJA
from pomagma.examples.testing import WORLD
from pomagma.examples.testing import serve
import pomagma.examples.solve


def _test_define(name):
    pomagma.examples.solve.define(name, address=ADDRESS)


def test_define():
    with serve(WORLD):
        for name in pomagma.examples.solve.theories:
            if name.endswith('_test'):
                yield _test_define, name
    with serve(SKJA):
        for name in pomagma.examples.solve.theories:
            yield _test_define, name


def test_sr_pairs():
    with serve(SKJA):
        pomagma.examples.solve.sr_pairs(address=ADDRESS)
