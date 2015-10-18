import pomagma.examples.synthesize
from pomagma.examples.testing import ADDRESS
from pomagma.examples.testing import SKJA
from pomagma.examples.testing import serve
from pomagma.util import in_temp_dir


def test_define():
    with serve(SKJA):
        pomagma.examples.synthesize.define_a(address=ADDRESS)


def test_profile():
    with serve(SKJA), in_temp_dir():
        pomagma.examples.synthesize.profile_a(address=ADDRESS)
