import os
import sys
import subprocess
import pomagma.util


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def init(theory, chart_out, size=None, **opts):
    if size is None:
        size = pomagma.util.MIN_SIZES[theory]
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'grower', pomagma.util.GROWERS[theory]),
        abspath(chart_out),
        size=size,
        **opts)


def grow(theory, chart_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'grower', pomagma.util.GROWERS[theory]),
        abspath(chart_in),
        abspath(chart_out),
        size=size,
        **opts)


def aggregate(atlas_in, chart_in, atlas_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'atlas', 'aggregate'),
        abspath(atlas_in),
        abspath(chart_in),
        abspath(atlas_out),
        **opts)


def trim(theory, atlas_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'atlas', 'trim'),
        abspath(atlas_in),
        abspath(chart_out),
        size,
        os.path.join(pomagma.util.THEORY, '{}.compiled'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        **opts)


def copy(chart_in, chart_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'atlas', 'copy'),
        abspath(chart_in),
        abspath(chart_out),
        **opts)
