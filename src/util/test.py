import time
import multiprocessing
from nose.tools import assert_equal
import pomagma.util


def _blocking_mutex((_id, curdir)):
    with pomagma.util.chdir(curdir), pomagma.util.mutex(block=True):
        print 'Running process', _id
        time.sleep(0.1)


def test_blocking_mutex():
    THREADS = 4
    pool = multiprocessing.Pool(THREADS)
    with pomagma.util.in_temp_dir() as curdir:
        args = [(_id, curdir) for _id in xrange(THREADS)]
        pool.map(_blocking_mutex, args)


def _nonblocking_mutex((_id, curdir)):
    try:
        with pomagma.util.chdir(curdir), pomagma.util.mutex(block=False):
            print 'Running process', _id
            time.sleep(0.1)
            return 1
    except pomagma.util.MutexLockedException:
        print 'Failing process', _id
        return 0


def test_nonblocking_mutex():
    THREADS = 4
    pool = multiprocessing.Pool(THREADS)
    with pomagma.util.in_temp_dir() as curdir:
        args = [(_id, curdir) for _id in xrange(THREADS)]
        runs = pool.map(_nonblocking_mutex, args)
    assert_equal(sum(runs), 1)
