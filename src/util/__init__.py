import contextlib
import email
import errno
import fcntl
import functools
import itertools
import os
import pdb
import shutil
import signal
import smtplib
import subprocess
import sys
import tempfile
import timeit
import traceback
import uuid

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SRC)
THEORY = os.path.join(SRC, 'theory')
LANGUAGE = os.path.join(SRC, 'language')
DATA = os.path.join(ROOT, 'data')
DB = '{}.pb'.format
BLOB_DIR = os.path.join(DATA, 'blob')
debug = int(os.environ.get('POMAGMA_DEBUG', 0))
if debug:
    print 'Running in debug mode'
    BUILD = os.path.join(ROOT, 'build', 'debug')
else:
    BUILD = os.path.join(ROOT, 'build', 'release')
BIN = os.path.join(BUILD, 'src')
NOTIFY_EMAIL = os.environ.get('POMAGMA_NOTIFY_EMAIL')
CLEANUP_ON_ERROR = int(os.environ.get('CLEANUP_ON_ERROR', 1))
COVERITY = os.path.join(ROOT, 'cov-int')
TRAVIS_CI = 'TRAVIS' in os.environ and 'CI' in os.environ

# TODO use standard levels from the logging module
LOG_LEVEL = int(os.environ.get('POMAGMA_LOG_LEVEL', 0))
LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

MIN_SIZES = {
    'h4': 127,
    'sk': 1023,
    'skj': 1535,
    'skja': 2047,
    'skrj': 2047,
}


def optimal_db_sizes():
    """Indefinitely iterate through optimal db sizes."""
    yield 512 - 1
    for i in itertools.count():
        yield 2 * 2 ** i * 512 - 1
        yield 3 * 2 ** i * 512 - 1


def suggest_region_sizes(min_size, max_size):
    """Return set of optimal db sizes in [min_size, max_size]"""
    sizes = []
    for size in optimal_db_sizes():
        if size > max_size:
            return sizes
        if size >= min_size:
            sizes.append(size)


def TODO(message=''):
    raise NotImplementedError('TODO {}'.format(message))


def unicode_to_str(data):
    '''
    Convert all unicode leaves of a json-like object to strings, in-place.
    '''
    if isinstance(data, unicode):
        data = str(data)
    elif isinstance(data, dict):
        for key, value in data.iteritems():
            data[key] = unicode_to_str(value)
    elif isinstance(data, (list, tuple)):
        for key, value in enumerate(data):
            data[key] = unicode_to_str(value)
    return data


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


def debuggable(fun):
    """Decorator for functions that start pdb on error."""

    @functools.wraps(fun)
    def debuggable_fun(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except:
            type, value, tb = sys.exc_info()
            traceback.print_exc()
            pdb.post_mortem(tb)

    return debuggable_fun


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
        print '# cd {}\n'.format(path)
        os.chdir(path)
        yield os.path.curdir
    finally:
        print '# cd {}\n'.format(old_path)
        os.chdir(old_path)


def temp_name(path):
    dirname, filename = os.path.split(path)
    # assert not filename.startswith('temp.'), path
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
    cleanup = CLEANUP_ON_ERROR
    try:
        with chdir(path):
            yield path
        cleanup = True
    finally:
        if cleanup:
            print '# rm -rf {}\n'.format(path)
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
            except IOError as e:
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
    options['blob_dir'] = os.path.abspath(options.get('blob_dir', BLOB_DIR))
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
    print 'file://{}'.format(log_file)
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
    tac = 'tail -r' if os.system('which tac') else 'tac'
    revgrep = '{tac} {file} | {grep} | {tac}'.format(
        tac=tac,
        file=log_file,
        grep=grep)
    subprocess.call(revgrep, shell=True)


def get_stack_trace(binary, pid):
    trace = '==== STACK TRACE ====\n'
    try:
        if sys.platform == 'darwin':
            trace += subprocess.check_output([
                'lldb',
                '-c', '/cores/core.{}'.format(pid),
                binary,
                '--batch',
                '-o', 'thread backtrace all',
                '-o', 'quit',
            ])
        else:
            trace += subprocess.check_output([
                'gdb',
                binary,
                'core',
                '--batch',
                '-ex', 'thread apply all bt',
                '-ex', 'quit',
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
    """Pass arguments to command line.

    Pass options into environment variables. Log process; if it crashes,
    dump stack trace to log file.

    """
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
        pid = proc.pid
        try:
            info = proc.wait()
        finally:
            if proc.poll() is None:
                proc.terminate()
    if info:
        print_logged_error(log_file)
        trace = get_stack_trace(args[0], pid)
        log_print(trace, log_file)
        sys.exit(info)


def log_Popen(*args, **options):
    """Pass arguments to command line.

    Pass options into environment variables. Log process.

    """
    args = map(str, args)
    args = options.pop('runner', '').split() + args
    extra_env = make_env(options)
    prepare_core_dump()
    print_command(args, extra_env)
    env = os.environ.copy()
    env.update(extra_env)
    return subprocess.Popen(args, env=env)


def use_memcheck(options, output='memcheck.out'):
    """Set options to run through valgrind memcheck.

    WARNING valgrind does not handle vector instructions well,
    so try compiling without -march=native.

    """
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


def notify(subject, content):
    """Send notification email to POMAGMA_NOTIFY_EMAIL or write to stderr."""
    if not NOTIFY_EMAIL:
        sys.stderr.write('POMAGMA_NOTIFY_EMAIL not set\n')
        sys.stderr.write('Subject: {}\n'.format(subject))
        sys.stderr.write('Message:\n{}\n'.format(content))
        sys.stderr.flush()
    message = email.mime.text.MIMEText(content)
    message['Subject'] = '[POMAGMA] {}'.format(subject)
    message['From'] = 'noreply@pomagma.org'
    message['To'] = NOTIFY_EMAIL
    s = smtplib.SMTP('localhost')
    s.sendmail(message['From'], [message['To']], message.as_string())
    s.quit()
