import pomagma.examples.synthesize
from pomagma.examples.testing import ADDRESS, SKJA, serve


def test_define_a():
    with serve(SKJA):
        pomagma.examples.synthesize.define_a(
            max_solutions=2, verbose=3, address=ADDRESS
        )


def test_define_a_pair():
    with serve(SKJA):
        pomagma.examples.synthesize.define_a_pair(
            max_solutions=2, verbose=3, address=ADDRESS
        )
