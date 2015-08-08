import contextlib
import pomagma.util
from pomagma.cartographer import server

serve = server.Server


@contextlib.contextmanager
def load(theory, world, address=None, **opts):
    with pomagma.util.log_duration():
        server = serve(theory, world, address, **opts)
        with server.connect() as client:
            yield client
            client.stop()
        server.wait()
