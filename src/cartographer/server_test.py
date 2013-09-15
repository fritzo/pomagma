import os
import pomagma.util
import pomagma.cartographer


def test_ping():
    theory = 'sk'
    data = os.path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', theory)
    if not os.path.exists(data):
        os.makedirs(data)
    world = os.path.join(data, '0.h5')  # HACK FIXME TODO
    address = 'ipc://{}'.format(os.path.join(data, 'socket'))
    print 'starting server'
    opts = {
        'log_file': os.path.join(data, 'test_ping.log'),
        'log_level': pomagma.util.LOG_LEVEL_DEBUG,
    }
    server = pomagma.cartographer.serve(theory, world, address, **opts)
    print 'connecting client'
    client = server.connect()
    for _ in xrange(10):
        print 'pinging server'
        client.ping()
        print 'stoping server'
        server.stop()
