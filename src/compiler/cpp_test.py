import os
import glob
from pomagma.compiler import run


def _test_compile(filename):
    run.compile(filename, outfile='temp.cpp')
    os.remove('temp.cpp')


def test_compile_rules():
    for filename in glob.glob('../theory/*.rules'):
        yield _test_compile, filename


def test_compile_facts():
    for filename in glob.glob('../theory/*.facts'):
        yield _test_compile, filename
