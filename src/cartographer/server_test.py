import os
import pomagma.util
import pomagma.surveyor
import pomagma.cartographer


def test_ping():
    theory = 'h4'
    data = os.path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', theory)
    world = os.path.join(data, '0.h5')
    if not os.path.exists(world):
        min_size = pomagma.util.MIN_SIZES[theory]
        pomagma.surveyor.init(theory, world, min_size)
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
