import os
import pomagma.util
import pomagma.cartographer.client
from pomagma.cartographer import messages_pb2 as messages
Request = messages.CartographerRequest


BIN = os.path.join(pomagma.util.BIN, 'cartographer')


class Server(object):

    def __init__(self, theory, world, address=None, **opts):
        if address is None:
            address = 'ipc://{}'.format(os.path.join(
                os.path.dirname(pomagma.util.abspath(world)),
                'cartographer.socket'))
        theory_file = os.path.join(
            pomagma.util.THEORY,
            '{}.compiled'.format(theory))
        language_file = os.path.join(
            pomagma.util.LANGUAGE,
            '{}.language'.format(theory))
        args = [
            os.path.join(BIN, 'cartographer'),
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
        return pomagma.cartographer.client.Client(self.address)

    def stop(self):
        if self._proc.poll() is None:
            self._proc.terminate()

    def kill(self):
        self._proc.kill()

    def wait(self):
        self._proc.wait()
