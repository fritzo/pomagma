import os
import sys
import glob
import shutil
import subprocess
import contextlib
import nose
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
def unit_test(*noseflags):
    '''
    Run unit tests.
    '''
    pomagma.util.check_call('nosetests', pomagma.util.SRC, *noseflags)
    pomagma.util.build()
    pomagma.util.test()


@parsable.command
def batch_test(theory='all'):
    '''
    Test batch operations.
    '''
    if theory == 'all':
        theories = pomagma.util.MIN_SIZES.keys()
        theories.sort(key=pomagma.util.MIN_SIZES.__getitem__)
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
def profile():
    '''
    Profile data structures.
    '''
    pomagma.util.build()
    buildtype = 'debug' if pomagma.util.debug else 'release'
    log_file = os.path.join(pomagma.util.LOG, buildtype + '.profile.log')
    if os.path.exists(log_file):
        os.remove(log_file)
    opts = dict(log_file=log_file, log_level=2)
    pattern = os.path.join(pomagma.util.BIN, '*', '*_profile')
    cmds = glob.glob(pattern)
    assert cmds, 'no profiles match {}'.format(pattern)
    for cmd in cmds:
        print 'Profiling', cmd
        pomagma.util.check_call(cmd, **opts)
    pomagma.util.check_call('cat', log_file)


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
