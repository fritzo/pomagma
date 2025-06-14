import contextlib
import os

import pomagma.util
from pomagma.analyst import client, server

ADDRESS = os.environ.get("POMAGMA_ANALYST_ADDRESS", "tcp://localhost:34936")


def connect(address=ADDRESS):
    return client.Client(address)


def serve(theory, world, address=ADDRESS, **opts):
    return server.Server(theory, world, address, **opts)


@contextlib.contextmanager
def load(theory, world, **opts):
    address = "ipc://{}".format(
        os.path.join(os.path.dirname(pomagma.util.abspath(world)), "analyst.socket")
    )
    with pomagma.util.log_duration():
        server = serve(theory, world, address, **opts)
        with server.connect() as client:
            yield client
        server.stop()
