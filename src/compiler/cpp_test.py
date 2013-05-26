import os
from pomagma.compiler import run
from pomagma.compiler.util import find_facts, find_rules


def _test_compile(filename):
    run.compile(filename, cpp_out='temp.cpp', theory_out='temp.compiled')
    os.remove('temp.cpp')
    os.remove('temp.compiled')


def test_compile_rules():
    for filename in find_rules():
        yield _test_compile, filename


def test_compile_facts():
    for filename in find_facts():
        yield _test_compile, filename
