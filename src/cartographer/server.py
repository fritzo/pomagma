import os
import subprocess
import pomagma.util
import pomagma.cartographer.client


BIN = os.path.join(pomagma.util.BIN, 'cartographer')


class Server(object):
    def __init__(self, theory, world, address=None, **opts):
        extra_env = pomagma.util.make_env(opts)
        cwd = os.path.join(pomagma.util.DATA, 'work', theory, 'cartographer')
        if address is None:
            address = 'ipc://{}'.format(os.path.join(cwd, 'socket'))
        theory_file = os.path.join(
            pomagma.util.THEORY,
            '{}.compiled'.format(theory))
        language_file = os.path.join(
            pomagma.util.LANGUAGE,
            '{}.language'.format(theory))
        args = [
            os.path.join(BIN, 'cartographer'),
            world,
            theory_file,
            language_file,
            address,
        ]
        assert os.path.exists(world), world
        assert os.path.exists(theory_file), theory_file
        assert os.path.exists(language_file), language_file
        if not os.path.exists(cwd):
            os.makedirs(cwd)
        self._theory = theory
        self._address = address
        pomagma.util.print_command(args, extra_env)
        env = os.environ.copy()
        env.update(extra_env)
        self._proc = subprocess.Popen(args, env=env, cwd=cwd)

    @property
    def theory(self):
        return self._theory

    @property
    def address(self):
        return self._address

    def connect(self):
        return pomagma.cartographer.client.Client(self.address)

    def stop(self):
        self._proc.terminate()

    def kill(self):
        self._proc.kill()
