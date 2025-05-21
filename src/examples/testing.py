import contextlib
import os

import pytest

import pomagma.util
from pomagma.atlas.bootstrap import THEORY, WORLD

assert WORLD  # pacify pyflakes

DATA = os.path.join(pomagma.util.DATA, "test", "debug", "atlas", THEORY)
ADDRESS = "ipc://{}".format(os.path.join(DATA, "analyst.socket"))
OPTIONS = {
    "log_file": os.path.join(DATA, "theorist_test.log"),
    "log_level": pomagma.util.LOG_LEVEL_DEBUG,
}

SKJA = os.path.join(
    pomagma.util.DATA,
    "atlas",
    "skja",
    "region.normal.{:d}.pb".format(pomagma.util.MIN_SIZES["skja"]),
)


@contextlib.contextmanager
def serve(world, address=ADDRESS):
    if not os.path.exists(world):
        pytest.skip("fixture not found")
    print("starting server")
    server = pomagma.analyst.serve(THEORY, world, address, **OPTIONS)
    yield server
    print("stopping server")
    server.stop()
