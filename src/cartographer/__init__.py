import os
import pomagma.util


BIN = os.path.join(pomagma.util.BIN, 'cartographer')


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
    Symmetrically combine two regions, extending langauges and merging facts.
    '''
    inputs = map(pomagma.util.abspath, [world_in, region_in])
    sizes = map(pomagma.util.get_item_count, inputs)
    if sizes[0] < sizes[1]:
        inputs.reverse()
    larger, smaller = inputs
    pomagma.util.log_call(
        os.path.join(BIN, 'aggregate'),
        larger,
        smaller,
        pomagma.util.abspath(world_out),
        **opts)


def infer(world_in, world_out, **opts):
    '''
    Infer simple facts.
    '''
    pomagma.util.log_call(
        os.path.join(BIN, 'infer'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(world_out),
        **opts)
