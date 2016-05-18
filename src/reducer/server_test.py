import os
import pomagma.reducer
import pomagma.util

DATA = os.path.join(pomagma.util.DATA, 'test', 'debug')
ADDRESS = 'ipc://{}'.format(os.path.join(DATA, 'socket'))
OPTIONS = {
    'log_file': os.path.join(DATA, 'reducer_test.log'),
    'log_level': pomagma.util.LOG_LEVEL_DEBUG,
}


def test_ping():
    print 'starting server'
    server = pomagma.reducer.serve(ADDRESS, **OPTIONS)
    try:
        print 'connecting client'
        with server.connect() as client:
            for _ in xrange(10):
                print 'pinging server'
                client.ping()
    finally:
        print 'stopping server'
        server.stop()
