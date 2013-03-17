import os
import sys
import subprocess
import multiprocessing
import contextlib
import tables

SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
THEORY = os.path.join(SRC, 'theory')
DATA = os.path.join(ROOT, 'data')
LOG = os.path.join(ROOT, 'log')
debug = 'POMAGMA_DEBUG' in os.environ
if debug:
    print 'Running in debug mode'
    BUILD = os.path.join(ROOT, 'build', 'debug')
else:
    BUILD = os.path.join(ROOT, 'build', 'release')
BIN = os.path.join(BUILD, 'src')

GROWERS = {
    'h4': 'h4.grow',
    'sk': 'sk.grow',
    'skj': 'skj.grow',
    }

MIN_SIZES = {
    'h4': 127,
    'sk': 1023,
    'skj': 1535,
    }


@contextlib.contextmanager
def chdir(path):
    old_path = os.path.abspath(os.path.curdir)
    try:
        #os.makedirs(path)
        sys.stderr.write('cd {}\n'.format(path))
        os.chdir(path)
        yield
    finally:
        sys.stderr.write('cd {}\n'.format(old_path))
        os.chdir(old_path)


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def make_env(**kwargs):
    kwargs['root'] = ROOT
    kwargs.setdefault('threads', multiprocessing.cpu_count())
    log_file = os.path.join(LOG, 'default.log')
    log_file = abspath(kwargs.get('log_file', log_file))
    kwargs['log_file'] = log_file
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    kwargs.setdefault('log_level', 4 if debug else 0)
    env = os.environ.copy()
    for key, val in kwargs.iteritems():
        pomagma_key = 'POMAGMA_{}'.format(key.upper())
        sys.stderr.write('{}={} \\\n'.format(pomagma_key, val))
        env[pomagma_key] = str(val)
    return env


def check_call(*args, **kwargs):
    env = make_env(**kwargs)
    sys.stderr.write('{}\n'.format(' \\\n'.join(args)))
    subprocess.check_call(args, env=env)


def build(*args, **kwargs):
    buildtype = 'Debug' if debug else 'RelWithDebInfo'
    buildflag = '-DCMAKE_BUILD_TYPE={}'.format(buildtype)
    if not os.path.exists(BUILD):
        os.makedirs(BUILD)
    with chdir(BUILD):
        check_call('cmake', buildflag, ROOT)
    check_call('make', '-C', BUILD, *args)


def count_obs(structure):
    # TODO return item_count rather than item_dim
    if isinstance(structure, basestring):
        structure = tables.openFile(structure)
    support = structure.getNode('/carrier/support')
    word_dim, = support.shape
    item_dim = 64 * word_dim - 1
    return item_dim  # only an upper bound on ob count


def print_info(infile):
    structure = tables.openFile(infile)
    item_count = count_obs(structure)
    print 'ob count <=', item_count
    for o in structure:
        print o
