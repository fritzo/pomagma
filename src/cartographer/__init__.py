import contextlib
import pomagma.util
from pomagma.cartographer import client
from pomagma.cartographer import server


connect = client.Client
serve = server.Server


@contextlib.contextmanager
def load(theory, world, address=None, **opts):
    with pomagma.util.log_duration():
        server = serve(theory, world, address, **opts)
        client = server.connect()
        yield client
        client.stop()
        server.wait()
