from pomagma.reducer.client import Client
from subprocess import CalledProcessError
import os
import pomagma.util

BINARY = os.path.join(pomagma.util.BIN, 'reducer', 'reducer')


class Server(object):

    def __init__(self, address=None, **opts):
        if address is None:
            address = 'ipc://{}'.format(
                os.path.join(pomagma.util.DATA, 'reducer.socket'))
        args = [BINARY, address]
        self._address = address
        self._dir = os.path.abspath(os.curdir)
        self._log_file = pomagma.util.get_log_file(opts)
        self._proc = pomagma.util.log_Popen(*args, **opts)

    @property
    def address(self):
        return self._address

    @property
    def pid(self):
        return self._proc.pid

    def connect(self):
        return Client(self.address, poll_callback=self.check)

    def stop(self):
        if self._proc.poll() is None:
            self._proc.terminate()

    def kill(self):
        self._proc.kill()

    def wait(self):
        if self._proc.wait() != 0:
            self.log_error()

    def check(self):
        if self._proc.poll() is not None:
            self.log_error()

    def log_error(self):
        pomagma.util.print_logged_error(self._log_file)
        with pomagma.util.chdir(self._dir):
            trace = pomagma.util.get_stack_trace(BINARY, self.pid)
        pomagma.util.log_print(trace, self._log_file)
        raise CalledProcessError(self._proc.poll(), BINARY)