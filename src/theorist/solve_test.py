from pomagma.theorist.testing import ADDRESS
from pomagma.theorist.testing import SKJA
from pomagma.theorist.testing import WORLD
from pomagma.theorist.testing import serve
import pomagma.theorist.solve


def _test_define(name):
    pomagma.theorist.solve.define(name, address=ADDRESS)


def test_define():
    with serve(WORLD):
        for name in pomagma.theorist.solve.theories:
            if name.endswith('_test'):
                yield _test_define, name
    with serve(SKJA):
        for name in pomagma.theorist.solve.theories:
            yield _test_define, name


def test_sr_pairs():
    with serve(SKJA):
        pomagma.theorist.solve.sr_pairs(address=ADDRESS)
