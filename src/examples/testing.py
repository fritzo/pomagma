from nose import SkipTest
from pomagma.atlas.bootstrap import THEORY
from pomagma.atlas.bootstrap import WORLD
import contextlib
import os
import pomagma.util

assert WORLD  # pacify pyflakes

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