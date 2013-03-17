import os
import sys
import subprocess
import contextlib
import tables
import parsable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
debug = 'POMAGMA_DEBUG' in os.environ
if debug:
    print 'Running in debug mode'
    BUILD = os.path.join(ROOT, 'build', 'debug')
    LOG_SUFFIX = '.debug.log'
else:
    BUILD = os.path.join(ROOT, 'build', 'release')
    LOG_SUFFIX = '.log'
BIN = os.path.join(BUILD, 'src')
LOG = os.path.join(ROOT, 'log')

THEORIES = ['h4', 'sk', 'skj']


def make_env(**kwargs):
    kwargs.setdefault('log_level', 4 if debug else 0)
    env = os.environ.copy()
    for key, val in kwargs.iteritems():
        pomagma_key = 'POMAGMA_{}'.format(key.upper())
        sys.stderr.write('{} = {} \\\n'.format(pomagma_key, val))
        env[pomagma_key] = str(val)
    return env


def call(*args, **kwargs):
    env = make_env(**kwargs)
    log_file = env['POMAGMA_LOG_FILE']
    sys.stderr.write('{}\n'.format(' \\\n'.join(args)))
    info = subprocess.call(args, env=env)
    if info:
        subprocess.call(['grep', '-C3', '-i', 'error', log_file])
    return info


@contextlib.contextmanager
def cd(path):
    old_path = os.path.abspath(os.path.curdir)
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_path)


@parsable.command
def build():
    '''
    Build pomagma tools from source.
    '''
    with cd(BUILD):
        call('cmake', ROOT)
        call('make')


def count_obs(structure):
    if isinstance(structure, basestring):
        structure = tables.openFile(structure)
    support = structure.getNode('/carrier/support')
    word_dim, = support.shape
    item_dim = 64 * word_dim - 1
    return item_dim  # only an upper bound on ob count


@parsable.command
def info(infile):
    '''
    Print information about a structure file.
    '''
    structure = tables.openFile(infile)
    item_count = count_obs(structure)
    print 'ob count <=', item_count
    for o in structure:
        print o


@parsable.command
def init(theory, infile, size_kobs=1):
    '''
    Initialize a structure with size kobs.
    '''
    assert theory in THEORIES, 'unknown theory: {}'.format(theory)
    tool = os.path.join(BIN, 'grower', '{}.grow'.format(theory))
    log_file = os.path.join(LOG, theory + LOG_SUFFIX)
    size = size_kobs * 1024 - 1
    call(tool, infile, size=size, log_file=log_file)


@parsable.command
def grow(theory, infile, outfile, size_kobs=1):
    '''
    Grow a structure by kobs.
    '''
    tool = os.path.join(BIN, 'grower', '{}.grow'.format(theory))
    log_file = os.path.join(LOG, theory + LOG_SUFFIX)
    size = count_obs(infile) + 1024 * size_kobs
    call(tool, infile, outfile, size=size, log_file=log_file)


@parsable.command
def aggregate(theory, atlas_in, chart_in, atlas_out):
    '''
    Grow a structure by kobs.
    '''
    tool = os.path.join(BIN, 'atlas', 'free.aggregate')
    log_file = os.path.join(LOG, theory + LOG_SUFFIX)
    call(tool, atlas_in, chart_in, atlas_out, log_file=log_file)


if __name__ == '__main__':
    sys.argv[0] = 'pomagma'
    parsable.dispatch()
