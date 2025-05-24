import multiprocessing
import time

import pomagma.util


def _blocking_mutex(args):
    (_id, curdir) = args
    with pomagma.util.chdir(curdir), pomagma.util.mutex(block=True):
        print("Running process"), _id
        time.sleep(0.1)


def test_blocking_mutex():
    THREADS = 4
    pool = multiprocessing.Pool(THREADS)
    with pomagma.util.in_temp_dir() as curdir:
        args = [(_id, curdir) for _id in range(THREADS)]
        pool.map(_blocking_mutex, args)


def _nonblocking_mutex(args):
    (_id, curdir) = args
    try:
        with pomagma.util.chdir(curdir), pomagma.util.mutex(block=False):
            print("Running process"), _id
            time.sleep(0.1)
            return 1
    except pomagma.util.MutexLockedException:
        print("Failing process"), _id
        return 0


def test_nonblocking_mutex():
    THREADS = 4
    pool = multiprocessing.Pool(THREADS)
    with pomagma.util.in_temp_dir() as curdir:
        args = [(_id, curdir) for _id in range(THREADS)]
        runs = pool.map(_nonblocking_mutex, args)
    assert sum(runs) == 1


def test_optimal_db_sizes():
    sizes = pomagma.util.optimal_db_sizes()
    assert next(sizes) == 1 * 512 - 1
    assert next(sizes) == 2 * 512 - 1
    assert next(sizes) == 3 * 512 - 1
    assert next(sizes) == 4 * 512 - 1
    assert next(sizes) == 6 * 512 - 1
    assert next(sizes) == 8 * 512 - 1
    assert next(sizes) == 12 * 512 - 1
    assert next(sizes) == 16 * 512 - 1


def test_suggest_region_sizes():
    sizes = pomagma.util.suggest_region_sizes(1023, 8888)
    assert sizes == [
        2 * 512 - 1,
        3 * 512 - 1,
        4 * 512 - 1,
        6 * 512 - 1,
        8 * 512 - 1,
        12 * 512 - 1,
        16 * 512 - 1,
    ]
