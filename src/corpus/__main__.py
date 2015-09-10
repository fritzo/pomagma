from parsable import parsable
from pomagma.util import TODO
import os
import pomagma.util

CORPUS = os.path.join(pomagma.util.SRC, 'corpus')


@parsable
def reformat(*files):
    '''
    Reformat code sections of specified markdown files in-place.
    This works recursively if given directories.
    '''
    TODO()


@parsable
def extract(filename):
    '''
    Extract code from markdown file.
    '''
    TODO()


@parsable
def annotate(*files):
    '''
    Annotate markdown files with high-latency results of analyst.
    '''
    TODO()


@parsable
def suggest(filename):
    '''
    Get real-time feedback from low-latency results of analyst.
    '''
    TODO()


@parsable
def precommit():
    '''
    Reformat and annotate all code before a git commit.
    '''
    reformat(CORPUS)


if __name__ == '__main__':
    parsable()
