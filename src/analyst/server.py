import os
from subprocess import CalledProcessError
import pomagma.util
from pomagma.analyst.client import Client

BINARY = os.path.join(pomagma.util.BIN, 'analyst', 'analyst')


class Server(object):

    def __init__(self, theory, world, address, threads, **opts):
        language_file = os.path.join(
            pomagma.util.LANGUAGE,
            '{}.language'.format(theory))
        args = [
            BINARY,
            pomagma.util.abspath(world),
            pomagma.util.abspath(language_file),
            address.replace('tcp://localhost', 'tcp://*'),
            threads,
        ]
        assert isinstance(address, basestring), address
        assert os.path.exists(world), world
        assert os.path.exists(language_file), language_file
        assert isinstance(threads, int)
        assert threads > 0
        self._theory = theory
        self._address = address
        self._dir = os.path.abspath(os.curdir)
        self._log_file = pomagma.util.get_log_file(opts)
        self._proc = pomagma.util.log_Popen(*args, **opts)

    @property
    def theory(self):
        return self._theory

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
            trace = pomagma.util.get_stack_trace(BINARY)
        pomagma.util.log_print(trace, self._log_file)
        raise CalledProcessError(self._proc.poll(), BINARY)
