#!/usr/bin/env python

import os
import subprocess
import parsable

REPO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(REPO)
TEMP = os.path.join(ROOT, '{}-temp'.format(os.path.basename(REPO)))


@parsable.command
def clone():
    '''
    Create temporary clone repo.
    '''
    os.chdir(REPO)
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'])
    commit = commit.strip()

    if os.path.exists(TEMP):
        print 'using clone {}'.format(TEMP)
        os.chdir(TEMP)
        subprocess.check_call(['git', 'fetch', '--all'])
    else:
        print 'cloning to {}'.format(TEMP)
        os.chdir(ROOT)
        subprocess.check_call(['git', 'clone', REPO, TEMP])

    os.chdir(TEMP)
    subprocess.check_call(['git', 'checkout', commit])


@parsable.command
def codegen(difftool='meld', *args):
    '''
    Diff all src/surveyor/*.theory.cpp.
    '''
    clone()

    os.chdir(REPO)
    subprocess.check_call(['make', 'codegen'])

    os.chdir(TEMP)
    subprocess.check_call(['make', 'codegen'])

    os.chdir(ROOT)
    subprocess.check_call([
        difftool] + list(args) + [
        os.path.join(REPO, 'src', 'surveyor'),
        os.path.join(TEMP, 'src', 'surveyor'),
    ])


if __name__ == '__main__':
    parsable.dispatch()
