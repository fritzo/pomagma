import os
from subprocess import CalledProcessError
from typing import Any

import pomagma.util
from pomagma.cartographer.client import Client

BINARY = os.path.join(pomagma.util.BIN, "cartographer", "cartographer")


class Server:
    def __init__(
        self, theory: str, world: str, address: str | None = None, **opts: Any
    ) -> None:
        if address is None:
            address = "ipc://{}".format(
                os.path.join(
                    os.path.dirname(pomagma.util.abspath(world)), "cartographer.socket"
                )
            )
        theory_file = os.path.join(pomagma.util.THEORY, f"{theory}.facts")
        language_file = os.path.join(pomagma.util.LANGUAGE, f"{theory}.language")
        args = [
            BINARY,
            pomagma.util.abspath(world),
            pomagma.util.abspath(theory_file),
            pomagma.util.abspath(language_file),
            address,
        ]
        assert os.path.exists(world), world
        assert os.path.exists(theory_file), theory_file
        assert os.path.exists(language_file), language_file
        self._theory = theory
        self._address = address
        self._dir = os.path.abspath(os.curdir)
        self._log_file = pomagma.util.get_log_file(opts)
        self._proc = pomagma.util.log_Popen(*args, **opts)

    @property
    def theory(self) -> str:
        return self._theory

    @property
    def address(self) -> str:
        return self._address

    @property
    def pid(self) -> int:
        pid = self._proc.pid
        if pid is None:
            raise RuntimeError("Process PID is not available")
        return pid

    def connect(self) -> Client:
        return Client(self.address, poll_callback=self.check)

    def stop(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()

    def kill(self) -> None:
        self._proc.kill()

    def wait(self) -> None:
        if self._proc.wait() != 0:
            self.log_error()

    def check(self) -> None:
        if self._proc.poll() is not None:
            self.log_error()

    def log_error(self) -> None:
        pomagma.util.print_logged_error(self._log_file)
        with pomagma.util.chdir(self._dir):
            trace = pomagma.util.get_stack_trace(BINARY, self.pid)
        pomagma.util.log_print(trace, self._log_file)
        raise CalledProcessError(self._proc.poll(), BINARY)
