from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, APP
from pomagma.util.testing import for_each
import os
import pomagma.reducer
import pomagma.util
import pytest

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
        'code': I,
        'budget': 0,
        'expected_code': I,
        'expected_budget': 0,
    },
    {
        'code': K,
        'budget': 0,
        'expected_code': K,
        'expected_budget': 0,
    },
    {
        'code': B,
        'budget': 0,
        'expected_code': B,
        'expected_budget': 0,
    },
    {
        'code': C,
        'budget': 0,
        'expected_code': C,
        'expected_budget': 0,
    },
    {
        'code': S,
        'budget': 0,
        'expected_code': S,
        'expected_budget': 0,
    },
    {
        'code': I,
        'budget': 1,
        'expected_code': I,
        'expected_budget': 1,
    },
    {
        'code': APP(I, I),
        'budget': 0,
        'expected_code': I,
        'expected_budget': 0,
    },
    {
        'code': APP(I, I),
        'budget': 1,
        'expected_code': I,
        'expected_budget': 1,
    },
    {
        'code': APP(K, TOP),
        'budget': 0,
        'expected_code': TOP,
        'expected_budget': 0,
    },
    {
        'code': APP(K, BOT),
        'budget': 0,
        'expected_code': BOT,
        'expected_budget': 0,
    },
    {
        'code': APP(B, I),
        'budget': 0,
        'expected_code': I,
        'expected_budget': 0,
    },
    {
        'code': APP(APP(C, B), I),
        'budget': 0,
        'expected_code': 'I',
        'expected_budget': 0,
        'xfail': 'TODO',
    },
]


@for_each(EXAMPLES)
def test_reduce(example):
    if 'xfail' in example:
        pytest.xfail(example['xfail'])
    with SERVER.connect() as client:
        client.reset()
        actual = client.reduce(example['code'], example['budget'])
        assert actual['code'] == example['expected_code']
        assert actual['budget'] == example['expected_budget']
