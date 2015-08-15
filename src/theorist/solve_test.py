from nose import SkipTest
from pomagma.atlas.bootstrap import THEORY
from pomagma.atlas.bootstrap import WORLD
import contextlib
import os
import pomagma.theorist.solve
import pomagma.util

DATA = os.path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', THEORY)
ADDRESS = 'ipc://{}'.format(os.path.join(DATA, 'socket'))
OPTIONS = {
    'log_file': os.path.join(DATA, 'theorist_test.log'),
    'log_level': pomagma.util.LOG_LEVEL_DEBUG,
}

SKJA = os.path.join(
    pomagma.util.DATA,
    'atlas',
    'skja',
    'region.normal.{:d}.pb'.format(pomagma.util.MIN_SIZES['skja']))


@contextlib.contextmanager
def serve(world, address=ADDRESS):
    if not os.path.exists(world):
        raise SkipTest('fixture not found')
    print 'starting server'
    server = pomagma.analyst.serve(THEORY, world, address, **OPTIONS)
    yield server
    print 'stopping server'
    server.stop()


def _test_define(name):
    pomagma.theorist.solve.define(name, address=ADDRESS)


def test_define():
    with serve(WORLD):
        for name in pomagma.theorist.solve.theories:
            if name.endswith('_test'):
                yield _test_define, name
    with serve(SKJA):
        for name in pomagma.theorist.solve.theories:
            yield _test_define, name


def test_sr_pairs():
    with serve(SKJA):
        pomagma.theorist.solve.sr_pairs(address=ADDRESS)
