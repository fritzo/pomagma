import os
import pomagma.util
import pomagma.cartographer


def test_ping():
    theory = 'sk'
    data = os.path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', theory)
    world = os.path.join(data, '0.h5')  # HACK FIXME TODO
    address = 'ipc://{}'.format(os.path.join(data, 'socket'))
    print 'starting server'
    server = pomagma.cartographer.serve(theory, world, address)
    print 'connecting client'
    client = server.connect()
    print 'pinging server'
    client.ping()
    print 'stoping server'
    server.stop()
