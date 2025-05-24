import pomagma.examples.solve
from pomagma.examples.testing import ADDRESS, SKJA, WORLD, serve
from pomagma.util.testing import for_each

WORLD_EXAMPLES = [
    (name, WORLD) for name in pomagma.examples.solve.theories if name.endswith("_test")
]

SKJA_EXAMPLES = [(name, SKJA) for name in pomagma.examples.solve.theories]


@for_each(WORLD_EXAMPLES + SKJA_EXAMPLES)
def test_define(name, theory):
    with serve(theory):
        pomagma.examples.solve.define(name, address=ADDRESS)


def test_rs_pairs():
    with serve(SKJA):
        pomagma.examples.solve.rs_pairs(address=ADDRESS)
