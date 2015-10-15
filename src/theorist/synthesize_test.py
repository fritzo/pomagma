from pomagma.theorist.testing import ADDRESS
from pomagma.theorist.testing import SKJA
from pomagma.theorist.testing import serve
import pomagma.theorist.synthesize


def test_define_a():
    with serve(SKJA):
        pomagma.theorist.synthesize.define_a(address=ADDRESS)
