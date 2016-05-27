from nose import SkipTest
from nose.tools import assert_equal
from pomagma.util.testing import for_each_kwargs
import os
import pomagma.reducer
import pomagma.util

DATA = os.path.join(pomagma.util.DATA, 'test', 'debug')
ADDRESS = 'ipc://{}'.format(os.path.join(DATA, 'reducer.socket'))
OPTIONS = {
    'log_file': os.path.join(DATA, 'reducer_test.log'),
    'log_level': pomagma.util.LOG_LEVEL_DEBUG,
}

SERVER = None


def setup_module():
    print 'starting server'
    global SERVER
    SERVER = pomagma.reducer.serve(ADDRESS, **OPTIONS)


def teardown_module():
    print 'stopping server'
    global SERVER
    SERVER.stop()
    SERVER = None


EXAMPLES = [
    {
        'code': 'I',
        'budget': 0,
        'expected_code': 'I',
        'expected_budget': 0,
        'skip': 'TODO',
    },
    {
        'code': 'I',
        'budget': 1,
        'expected_code': 'I',
        'expected_budget': 1,
        'skip': 'TODO',
    },
    {
        'code': 'APP I I',
        'budget': 0,
        'expected_code': 'I',
        'expected_budget': 0,
        'skip': 'TODO',
    },
]


@for_each_kwargs(EXAMPLES)
def test_reduce(code, budget, expected_code, expected_budget, skip=None):
    if skip:
        raise SkipTest(skip)
    with SERVER.connect() as client:
        client.reset()
        actual = client.reduce(code, budget)
        assert_equal(actual['code'], expected_code)
        assert_equal(actual['budget'], expected_budget)
