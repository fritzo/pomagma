import os

import pomagma.cartographer
import pomagma.util
from pomagma.atlas.bootstrap import THEORY, WORLD

DATA = os.path.join(pomagma.util.DATA, "test", "debug", "atlas", THEORY)
ADDRESS = "ipc://{}".format(os.path.join(DATA, "cartographer.socket"))
OPTIONS = {
    "log_file": os.path.join(DATA, "cartographer_test.log"),
    "log_level": pomagma.util.LOG_LEVEL_DEBUG,
}


def test_ping():
    print("starting server")
    server = pomagma.cartographer.serve(THEORY, WORLD, ADDRESS, **OPTIONS)
    try:
        print("connecting client")
        with server.connect() as client:
            for _ in range(10):
                print("pinging server")
                client.ping()
    finally:
        print("stopping server")
        server.stop()
