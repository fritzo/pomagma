from pomagma.reducer.syntax import I, K, B, C, S, BOT, TOP, APP
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
    print('starting server')
    global SERVER
    SERVER = pomagma.reducer.serve(ADDRESS, **OPTIONS)


def teardown_module():
    print('stopping server')
    global SERVER
    SERVER.stop()
    SERVER = None


@for_each([
    (I, 0, I, 0),
    (K, 0, K, 0),
    (B, 0, B, 0),
    (C, 0, C, 0),
    (S, 0, S, 0),
    (I, 1, I, 1),
    (APP(I, I), 0, I, 0),
    (APP(I, I), 1, I, 1),
    (APP(K, TOP), 0, TOP, 0),
    (APP(K, BOT), 0, BOT, 0),
    (APP(B, I), 0, I, 0),
    pytest.mark.xfail((APP(APP(C, B), I), 0, I, 0)),
])
def test_reduce(code, budget, expected_code, expected_budget):
    with SERVER.connect() as client:
        client.reset()
        actual = client.reduce(code, budget)
        assert actual['code'] == expected_code
        assert actual['budget'] == expected_budget
