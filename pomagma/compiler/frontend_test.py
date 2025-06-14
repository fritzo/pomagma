import pomagma.util
from pomagma.compiler import __main__ as main
from pomagma.compiler.util import find_theories
from pomagma.util.testing import for_each


@for_each(find_theories())
def test_compile(filename):
    with pomagma.util.in_temp_dir():
        main.compile(
            filename,
            symbols_out="temp.symbols",
            facts_out="temp.facts",
            programs_out="temp.programs",
            optimized_out="temp.optimized.programs",
        )
