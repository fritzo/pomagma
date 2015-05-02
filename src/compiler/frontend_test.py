import pomagma.util
from pomagma.compiler import __main__ as main
from pomagma.compiler.util import find_theories


def _test_compile(filename):
    with pomagma.util.in_temp_dir():
        main.compile(
            filename,
            symbols_out='temp.symbols',
            facts_out='temp.facts',
            programs_out='temp.programs',
            optimized_out='temp.optimized.programs')


def test_compile_rules():
    for filename in find_theories():
        yield _test_compile, filename


def test_compile_facts():
    for filename in find_theories():
        yield _test_compile, filename
