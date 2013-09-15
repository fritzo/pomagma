import os
import contextlib
import pomagma.util
from pomagma.cartographer import client
from pomagma.cartographer import server


BIN = os.path.join(pomagma.util.BIN, 'cartographer')

connect = client.Client
serve = server.Server


@contextlib.contextmanager
def load(theory, world, address=None, **opts):
    with pomagma.util.log_duration():
        server = serve(theory, world, address, **opts)
        yield server.connect()
        server.stop()


def validate(chart_in, **opts):
    pomagma.util.log_call(
        os.path.join(BIN, 'validate'),
        pomagma.util.abspath(chart_in),
        **opts)


def copy(chart_in, chart_out, **opts):
    pomagma.util.log_call(
        os.path.join(BIN, 'copy'),
        pomagma.util.abspath(chart_in),
        pomagma.util.abspath(chart_out),
        **opts)


def trim(theory, world_in, region_out, size, **opts):
    '''
    Randomly trim a world map down to region of given size.
    '''
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    pomagma.util.log_call(
        os.path.join(BIN, 'trim'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(region_out),
        size,
        os.path.join(pomagma.util.THEORY, '{}.compiled'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        **opts)


def aggregate(world_in, region_in, world_out, **opts):
    '''
    Combine two regions, restricting and extending langauges and merging facts.
    '''
    pomagma.util.log_call(
        os.path.join(BIN, 'aggregate'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(region_in),
        pomagma.util.abspath(world_out),
        **opts)


def infer(world_in, world_out, steps, **opts):
    '''
    Infer simple facts.
    '''
    pomagma.util.log_call(
        os.path.join(BIN, 'infer'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(world_out),
        steps,
        **opts)
