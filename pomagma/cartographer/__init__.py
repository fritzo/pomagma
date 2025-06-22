import contextlib
from collections.abc import Generator
from typing import Any

import pomagma.util
from pomagma.cartographer import server
from pomagma.cartographer.client import Client

serve = server.Server


@contextlib.contextmanager
def load(
    theory: str, world: str, address: str | None = None, **opts: Any
) -> Generator[Client, None, None]:
    with pomagma.util.log_duration():
        server = serve(theory, world, address, **opts)
        with server.connect() as client:
            yield client
            client.stop()
        server.wait()
