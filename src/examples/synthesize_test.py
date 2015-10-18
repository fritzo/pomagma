import pomagma.examples.synthesize
from pomagma.examples.testing import ADDRESS
from pomagma.examples.testing import SKJA
from pomagma.examples.testing import serve


def test_define():
    with serve(SKJA):
        pomagma.examples.synthesize.define_a(address=ADDRESS)
