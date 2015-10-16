from pomagma.examples.testing import ADDRESS
from pomagma.examples.testing import SKJA
from pomagma.examples.testing import serve
import pomagma.examples.synthesize


def test_define_a():
    with serve(SKJA):
        pomagma.examples.synthesize.define_a(address=ADDRESS)
