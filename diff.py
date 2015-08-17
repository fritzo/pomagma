#!/usr/bin/env python

import contextlib
import os
from parsable import parsable
import subprocess

REPO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(REPO)
TEMP = os.path.join(ROOT, '{}-temp'.format(os.path.basename(REPO)))
DIFFTOOL = os.environ.get('POMAGMA_DIFFTOOL', os.environ.get('EDITOR', 'meld'))


def get_difftool(tool, left, right, diffignore):
    if tool == 'diff':
        return (
            ['diff', '-r'] +
            map('--exclude={}'.format, diffignore) +
            [left, right])
    elif tool == 'cdiff':
        return ['cdiff', '-s', '-w', '0', left, right]
    elif tool == 'vim':
        return [
            'vim',
            '-c', 'let g:DirDiffExcludes = "{}"'.format(','.join(diffignore)),
            '-c', 'DirDiff {} {}'.format(left, right),
        ]
    elif tool == 'gvim':
        return [
            'gvim', '-geom', '165x80',
            '-c', 'let g:DirDiffExcludes = "{}"'.format(','.join(diffignore)),
            '-c', 'DirDiff {} {}'.format(left, right),
        ]
    elif tool == 'mvim':
        return [
            'mvim', '-c', 'set columns=165',
            '-c', 'let g:DirDiffExcludes = "{}"'.format(','.join(diffignore)),
            '-c', 'DirDiff {} {}'.format(left, right),
        ]
    else:
        return [tool, left, right]


def parallel_check_call(*args):
    for proc in map(subprocess.Popen, args):
        proc.wait()


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


@parsable
def clone(commit='HEAD'):
    '''
    Create temporary clone repo in ../ positioned at the given commit.
    '''
    with chdir(REPO):
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--verify', commit]).strip()

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


@parsable
def codegen(commit='HEAD', difftool=DIFFTOOL):
    '''
    Diff generated code src/theory/*.symbols, *.programs, *.facts
    Supported difftools: diff, meld, cdiff, vim, gvim, mvim
    '''
    clone(commit=commit)
    parallel_check_call(
        ['make', '-C', REPO, 'codegen'],
        ['make', '-C', TEMP, 'codegen'])
    subprocess.check_call(get_difftool(
        difftool,
        os.path.join(REPO, 'src', 'theory'),
        os.path.join(TEMP, 'src', 'theory'),
        diffignore=[
            '*.tasks',
            '*.rules',
            '*.theory',
            '*.pyc',
        ],
    ))


@parsable
def codegen_summary(commit='HEAD', difftool=DIFFTOOL):
    '''
    Diff generated code sommary in src/theory/*.tasks.
    Supported difftools: diff, meld, cdiff, vim, gvim, mvim
    '''
    clone(commit=commit)
    parallel_check_call(
        ['make', '-C', REPO, 'codegen-summary'],
        ['make', '-C', TEMP, 'codegen-summary'])
    subprocess.check_call(get_difftool(
        difftool,
        os.path.join(REPO, 'src', 'theory'),
        os.path.join(TEMP, 'src', 'theory'),
        diffignore=[
            '*.symbols',
            '*.programs',
            '*.facts',
            '*.rules',
            '*.theory',
            '*.pyc',
        ],
    ))


if __name__ == '__main__':
    parsable()
