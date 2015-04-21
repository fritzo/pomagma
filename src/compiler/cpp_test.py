import os
from pomagma.compiler import __main__ as main
from pomagma.compiler.util import find_theories


def _test_compile(filename):
    main.compile(
        filename,
        cpp_out='temp.cpp',
        symbols_out='temp.symbols',
        facts_out='temp.facts',
        programs_out='temp.programs')
    os.remove('temp.cpp')
    os.remove('temp.symbols')
    os.remove('temp.facts')
    os.remove('temp.programs')


def test_compile_rules():
    for filename in find_theories():
        yield _test_compile, filename


def test_compile_facts():
    for filename in find_theories():
        yield _test_compile, filename
