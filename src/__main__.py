import os
import sys
import shutil
import subprocess
import contextlib
import parsable
import pomagma.util
import pomagma.wrapper
import pomagma.batch


@parsable.command
def build():
    '''
    Build pomagma tools from source.
    '''
    pomagma.util.build()


@parsable.command
def info(infile):
    '''
    Print information about a structure file.
    '''
    pomagma.util.print_info(infile)


@parsable.command
def unit_test():
    '''
    Run unit tests.
    '''
    buildtype = 'debug' if pomagma.util.debug else 'release'
    opts = {
        'log_file': os.path.join(pomagma.util.LOG, buildtype + '.test.log'),
        'log_level': 3,
        }
    pomagma.util.build('test', **opts)
    # TODO show log file upon error, as done in batch_test


@parsable.command
def batch_test(theory='all'):
    '''
    Test batch operations.
    '''
    if theory == 'all':
        theories = pomagma.util.MIN_SIZES.keys()
        theories.sort(key=pomagma.util.MIN_SIZES.__getitem__)
        for theory in theories:
            test_batch(theory)
    else:
        theories = [theory]

    print '-' * 78
    print 'Building'
    pomagma.util.build()
    for theory in theories:
        print '-' * 78
        print 'Testing', theory
        pomagma.batch.test(theory)


@parsable.command
def clean():
    '''
    Clean out temporary files: build, log, data
    '''
    with pomagma.util.chdir(pomagma.util.ROOT):
        for temp in ['build', 'log', 'data']:
            if os.path.exists(temp):
                shutil.rmtree(temp)


if __name__ == '__main__':
    sys.argv[0] = 'pomagma'
    parsable.dispatch()
