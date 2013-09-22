import os
import pomagma.util
import pomagma.analyst.client


BIN = os.path.join(pomagma.util.BIN, 'analyst')


class Server(object):
    def __init__(self, theory, world, address, **opts):
        language_file = os.path.join(
            pomagma.util.LANGUAGE,
            '{}.language'.format(theory))
        args = [
            os.path.join(BIN, 'analyst'),
            pomagma.util.abspath(world),
            pomagma.util.abspath(language_file),
            address.replace('tcp://localhost', 'tcp://*'),
        ]
        assert isinstance(address, basestring), address
        assert os.path.exists(world), world
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

    def connect(self):
        return pomagma.analyst.client.Client(self.address)

    def stop(self):
        self._proc.terminate()

    def kill(self):
        self._proc.kill()

    def wait(self):
        self._proc.wait()
