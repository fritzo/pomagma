import os
import pomagma.util


def validate(chart_in, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'validate'),
        pomagma.util.abspath(chart_in),
        **opts)


def copy(chart_in, chart_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'copy'),
        pomagma.util.abspath(chart_in),
        pomagma.util.abspath(chart_out),
        **opts)


def trim(theory, world_in, region_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'trim'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(region_out),
        size,
        os.path.join(pomagma.util.THEORY, '{}.compiled'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        **opts)


def aggregate(world_in, region_in, world_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'aggregate'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(region_in),
        pomagma.util.abspath(world_out),
        **opts)
