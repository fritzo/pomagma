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
CPU_COUNT = multiprocessing.cpu_count()

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


class PomagmaError(Exception):
    pass


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


@contextlib.contextmanager
def load(filename):
    structure = tables.openFile(filename)
    yield structure
    structure.close()


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def make_env(**kwargs):
    kwargs['root'] = ROOT
    kwargs.setdefault('threads', CPU_COUNT)
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
    env = make_env(**kwargs) if kwargs else None
    sys.stderr.write('{}\n'.format(' \\\n'.join(args)))
    info = subprocess.call(args, env=env)
    if info:
        if 'log_file' in kwargs:
            log_file = kwargs['log_file']
            subprocess.call([
                'grep',
				'--context=3',
				'--ignore-case',
				'--color=always',
				'error',
				log_file,
                ])
            subprocess.call([
                'gdb',
                args[0],
                'core',
                '--batch',
                '-ex',
                'thread apply all bt',
                ])
        raise PomagmaError(' '.join(args))


def build():
    buildtype = 'Debug' if debug else 'RelWithDebInfo'
    buildflag = '-DCMAKE_BUILD_TYPE={}'.format(buildtype)
    if not os.path.exists(BUILD):
        os.makedirs(BUILD)
    with chdir(BUILD):
        check_call('cmake', buildflag, ROOT)
        check_call('make', '--quiet', '-j', str(1 + CPU_COUNT))


def test():
    build()
    buildtype = 'debug' if debug else 'release'
    opts = {
        'log_file': os.path.join(LOG, '{}.test.log'.format(buildtype)),
        'log_level': 3,
        }
    check_call('make', '-C', BUILD, 'test', **opts)


def count_obs(structure):
    points = structure.getNode('/carrier/points')
    item_dim = max(points)
    item_count, = points.shape
    return item_dim, item_count


def get_hash(infile):
    with load(infile) as structure:
        digest = structure.getNodeAttr('/', 'hash').tolist()
        return digest


def print_info(infile):
    with load(infile) as structure:
        item_dim, item_count = count_obs(structure)
        print 'item_dim =', item_dim
        print 'item_count =', item_count
        for o in structure:
            print o
