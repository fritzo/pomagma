import os
import glob
from pomagma.compiler import run


def _test_cpp(filename):
    run.compile(filename, outfile='temp.cpp')
    os.remove('temp.cpp')


def test_cpp():
    for filename in glob.glob('../theory/*.rules'):
        yield _test_cpp, filename
