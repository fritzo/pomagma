#!/usr/bin/env python

import os
import contextlib
import subprocess
import parsable

REPO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(REPO)
TEMP = os.path.join(ROOT, '{}-temp'.format(os.path.basename(REPO)))


@contextlib.contextmanager
def chdir(destin):
    source = os.curdir
    try:
        print '# cd'.format(destin)
        os.chdir(destin)
        yield
    finally:
        print '# cd'.format(source)
        os.chdir(source)

@parsable.command
def clone():
    '''
    Create temporary clone repo.
    '''
    with chdir(REPO):
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--verify', 'HEAD']).strip()

    if os.path.exists(TEMP):
        print 'using clone {}'.format(TEMP)
        with chdir(TEMP):
            subprocess.check_call(['git', 'fetch', '--all'])
    else:
        print 'cloning to {}'.format(TEMP)
        with chdir(ROOT):
            subprocess.check_call(['git', 'clone', REPO, TEMP])

    with chdir(TEMP):
        subprocess.check_call(['git', 'checkout', commit])


@parsable.command
def codegen(difftool='meld', *args):
    '''
    Diff all src/surveyor/*.theory.cpp.
    '''
    clone()
    subprocess.check_call(['make', '-C', REPO, 'codegen'])
    subprocess.check_call(['make', '-C', TEMP, 'codegen'])
    subprocess.check_call([
        difftool] + list(args) + [
        os.path.join(REPO, 'src', 'surveyor'),
        os.path.join(TEMP, 'src', 'surveyor'),
    ])


if __name__ == '__main__':
    parsable.dispatch()
