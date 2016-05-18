import os
import contextlib
import pomagma.util
from pomagma.reducer import client
from pomagma.reducer import server


ADDRESS = os.environ.get('POMAGMA_REDUCER_ADDRESS', 'tcp://localhost:34937')


def connect(address=ADDRESS):
    return client.Client(address)


def serve(address=ADDRESS, **opts):
    return server.Server(address, **opts)


@contextlib.contextmanager
def load(**opts):
    address = 'ipc://{}'.format(
        os.path.join(pomagma.util.DATA), 'analyst.socket')
    with pomagma.util.log_duration():
        server = serve(address, **opts)
        with server.connect() as client:
            yield client
        server.stop()
