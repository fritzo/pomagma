import os
import sys
import fcntl
import errno
import signal
import shutil
import subprocess
import multiprocessing
import contextlib
import uuid
import tempfile
import timeit


SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
THEORY = os.path.join(SRC, 'theory')
LANGUAGE = os.path.join(SRC, 'language')
DATA = os.path.join(ROOT, 'data')
debug = int(os.environ.get('POMAGMA_DEBUG', 0))
if debug:
    print 'Running in debug mode'
    BUILD = os.path.join(ROOT, 'build', 'debug')
else:
    BUILD = os.path.join(ROOT, 'build', 'release')
COVERITY = os.path.join(ROOT, 'cov-int')
BIN = os.path.join(BUILD, 'src')
TRAVIS_CI = 'TRAVIS' in os.environ and 'CI' in os.environ
CPU_COUNT = 2 if TRAVIS_CI else multiprocessing.cpu_count()

LOG_LEVEL = int(os.environ.get('POMAGMA_LOG_LEVEL', 0))
LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

MIN_SIZES = {
    'h4': 127,
    'sk': 1023,
    'skj': 1535,
    'skrj': 2047,
}


def on_signal(sig):
    def decorator(handler):
        signal.signal(sig, handler)
        return handler
    return decorator


# adapted from
# http://blog.devork.be/2009/07/how-to-bring-running-python-program.html
@on_signal(signal.SIGUSR1)
def handle_pdb(sig, frame):
    import pdb
    pdb.Pdb().set_trace(frame)


def get_rss(pid):
    try:
        return int(subprocess.check_output(['ps', '-o', 'rss=', str(pid)]))
    except subprocess.CalledProcessError:
        return 0


def print_dot(out=sys.stdout):
    out.write('.')
    out.flush()


def random_uuid():
    return str(uuid.uuid4())


@contextlib.contextmanager
def chdir(path):
    old_path = os.path.abspath(os.path.curdir)
    try:
        # os.makedirs(path)
        print 'cd {}\n'.format(path)
        os.chdir(path)
        yield os.path.curdir
    finally:
        print 'cd {}\n'.format(old_path)
        os.chdir(old_path)


def temp_name(path):
    dirname, filename = os.path.split(path)
    assert not filename.startswith('temp.'), path
    return os.path.join(dirname, 'temp.{}.{}'.format(os.getpid(), filename))


@contextlib.contextmanager
def temp_copy(path):
    dirname = os.path.dirname(path)
    assert not dirname or os.path.exists(dirname), path
    temp = temp_name(path)
    if os.path.exists(temp):
        shutil.rmtree(temp)
    yield temp
    if os.path.exists(temp):
        os.rename(temp, path)
    elif os.path.exists(path):
        os.remove(path)


@contextlib.contextmanager
def temp_copies(paths):
    temps = []
    for path in paths:
        dirname = os.path.dirname(path)
        assert not dirname or os.path.exists(dirname), path
        temp = temp_name(path)
        if os.path.exists(temp):
            shutil.rmtree(temp)
        temps.append(temp)
    yield temps
    for temp, path in zip(temps, paths):
        if os.path.exists(temp):
            os.rename(temp, path)
        elif os.path.exists(path):
            os.remove(path)


@contextlib.contextmanager
def in_temp_dir():
    path = os.path.abspath(tempfile.mkdtemp())
    try:
        with chdir(path):
            yield path
    finally:
        shutil.rmtree(path)


class MutexLockedException(Exception):

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)

    def __str__(self):
        return 'Failed to acquire lock on {}'.format(self.filename)


# Adapted from:
# http://blog.vmfarms.com/2011/03/cross-process-locking-and.html
@contextlib.contextmanager
def mutex(filename=None, block=True):
    if filename is None:
        mutex_filename = 'mutex'
    elif os.path.isdir(filename):
        mutex_filename = os.path.join(filename, 'mutex')
    else:
        mutex_filename = '{}.mutex'.format(filename)
    with open(mutex_filename, 'w') as fd:
        if block:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                fd.write('{}\n'.format(os.getpid()))
                fd.flush()
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        else:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fd.write('{}\n'.format(os.getpid()))
                fd.flush()
            except IOError, e:
                assert e.errno in [errno.EACCES, errno.EAGAIN]
                raise MutexLockedException(mutex_filename)
            else:
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def log_duration():
    try:
        start_time = timeit.default_timer()
        yield
    finally:
        duration = timeit.default_timer() - start_time
        print '# took {:0.3g} sec'.format(duration)


@contextlib.contextmanager
def h5_open(filename):
    import tables
    structure = tables.openFile(filename)
    yield structure
    structure.close()


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def ensure_abspath(filename):
    filename = abspath(filename)
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return filename


def get_log_file(options):
    log_file = os.path.join(DATA, 'default.log')
    log_file = abspath(options.get('log_file', log_file))
    return log_file


def log_print(message, log_file):
    with open(log_file, 'a') as log:
        log.write(message)
        log.write('\n')
    print message


def make_env(options):
    options = dict(options)
    log_file = get_log_file(options)
    options['log_file'] = log_file
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    default_log_level = LOG_LEVEL_DEBUG if debug else LOG_LEVEL_INFO
    options.setdefault('log_level', default_log_level)
    env = {
        'POMAGMA_{}'.format(key.upper()): str(val)
        for key, val in options.iteritems()
    }
    return env


def print_command(args, env={}):
    lines = ['{}={}'.format(key, val) for key, val in env.iteritems()]
    lines += args
    message = '{}\n'.format(' \\\n  '.join(lines))
    sys.stderr.write(message)


def check_call(*args):
    print_command(args)
    with log_duration():
        proc = subprocess.Popen(args)
        try:
            info = proc.wait()
        finally:
            if proc.poll() is None:
                proc.terminate()
    if info:
        sys.stderr.write('ERROR in {}'.format(' '.join(args)))
        sys.exit(info)


def print_logged_error(log_file):
    print
    print '==== LOG FILE ===='
    grep = ' '.join([
        'grep',
        '--before-context=40',
        '--after-context=3',
        '--ignore-case',
        '--color=always',
        '--text',
        '--max-count=1',
        'error'
    ])
    revgrep = 'tac {} | {} | tac'.format(log_file, grep)
    subprocess.call(revgrep, shell=True)


def get_stack_trace(binary):
    trace = '==== STACK TRACE ====\n'
    try:
        trace += subprocess.check_output([
            'gdb',
            binary,
            'core',
            '--batch',
            '-ex',
            'thread apply all bt',
        ])
    except subprocess.CalledProcessError:
        trace += 'ERROR stack trace failed'
    return trace


def prepare_core_dump():
    if os.path.exists('core'):
        os.remove('core')
    if subprocess.check_output('ulimit -c', shell=True).strip() == '0':
        print 'WARNING cannot write core file; try `ulimit -c unlimited`'


def log_call(*args, **options):
    '''
    Pass arguments to command line.
    Pass options into environment variables.
    Log process; if it crashes, dump stack trace to log file.
    '''
    args = map(str, args)
    args = options.pop('runner', '').split() + args
    extra_env = make_env(options)
    log_file = extra_env['POMAGMA_LOG_FILE']
    prepare_core_dump()
    print_command(args, extra_env)
    env = os.environ.copy()
    env.update(extra_env)
    with log_duration():
        proc = subprocess.Popen(args, env=env)
        try:
            info = proc.wait()
        finally:
            if proc.poll() is None:
                proc.terminate()
    if info:
        print_logged_error(log_file)
        trace = get_stack_trace(args[0])
        log_print(trace, log_file)
        sys.exit(info)


def log_Popen(*args, **options):
    '''
    Pass arguments to command line.
    Pass options into environment variables.
    Log process.
    '''
    args = map(str, args)
    args = options.pop('runner', '').split() + args
    extra_env = make_env(options)
    prepare_core_dump()
    print_command(args, extra_env)
    env = os.environ.copy()
    env.update(extra_env)
    return subprocess.Popen(args, env=env)


def use_memcheck(options, output='memcheck.out'):
    '''
    Set options to run through valgrind memcheck.
    WARNING valgrind does not handle vector instructions well,
    so try compiling without -march=native.
    '''
    suppressions = os.path.join(SRC, 'zmq.valgrind.suppressions')
    options = options.copy()
    options['runner'] = ' '.join([
        'valgrind',
        '--leak-check=full',
        '--show-reachable=yes',
        '--track-origins=yes',
        '--log-file={}'.format(output),
        '--suppressions={}'.format(suppressions),
    ])
    return options


def coverity():
    '''
    See http://scan.coverity.com
    '''
    buildtype = 'Debug'
    buildflag = '-DCMAKE_BUILD_TYPE={}'.format(buildtype)
    for d in [BUILD, COVERITY]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    with chdir(BUILD):
        check_call('cmake', buildflag, ROOT)
        check_call('cov-build', '--dir', COVERITY, 'make')


def count_obs(structure):
    points = structure.getNode('/carrier/points')
    item_dim = max(points)
    item_count, = points.shape
    return item_dim, item_count


def get_hash(infile):
    with h5_open(infile) as structure:
        digest = structure.getNodeAttr('/', 'hash').tolist()
        return digest


def get_info(infile):
    with h5_open(infile) as structure:
        item_dim, item_count = count_obs(structure)
        info = dict(item_dim=item_dim, item_count=item_count)
        return info


def get_item_count(infile):
    with h5_open(infile) as structure:
        item_dim, item_count = count_obs(structure)
        info = dict(item_dim=item_dim, item_count=item_count)
        return info['item_count']


def print_info(infile):
    with h5_open(infile) as structure:
        item_dim, item_count = count_obs(structure)
        print 'item_dim =', item_dim
        print 'item_count =', item_count
        for o in structure:
            print o
