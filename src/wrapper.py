import os
import sys
import subprocess
import pomagma.util


class PomagmaError(Exception):
    pass


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def call(*args, **kwargs):
    env = pomagma.util.make_env(**kwargs)
    log_file = kwargs['log_file']
    sys.stderr.write('{}\n'.format(' \\\n'.join(args)))
    info = subprocess.call(args, env=env)
    if info:
        subprocess.call(['grep', '-C3', '-i', 'error', log_file])
        subprocess.call([
            'gdb', args[0], 'core', '--batch', '-ex', 'thread apply all bt',
            ])
        raise PomagmaError(' '.join(args))


def init(theory, chart_out, size, **opts):
    call(
        os.path.join(pomagma.util.BIN, 'grower', pomagma.util.GROWERS[theory]),
        abspath(chart_out),
        size=size,
        **opts)


def grow(theory, chart_in, chart_out, size, **opts):
    call(
        os.path.join(pomagma.util.BIN, 'grower', pomagma.util.GROWERS[theory]),
        abspath(chart_in),
        abspath(chart_out),
        size=size,
        **opts)


def aggregate(atlas_in, chart_in, atlas_out, **opts):
    call(
        os.path.join(pomagma.util.BIN, 'atlas', 'aggregate'),
        abspath(atlas_in),
        abspath(chart_in),
        abspath(atlas_out),
        **opts)


def copy(chart_in, chart_out, **opts):
    call(
        os.path.join(pomagma.util.BIN, 'atlas', 'copy'),
        abspath(chart_in),
        abspath(chart_out),
        **opts)
