import glob
from pomagma import run

def test_cpp():
    for filename in glob.glob('*.rules'):
        yield run.test_compile, filename
