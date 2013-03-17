import os
import sys
import subprocess
import pomagma.util


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def init(theory, chart_out, size, **opts):
    pomagma.util.check_call(
        os.path.join(pomagma.util.BIN, 'grower', pomagma.util.GROWERS[theory]),
        abspath(chart_out),
        size=size,
        **opts)


def grow(theory, chart_in, chart_out, size, **opts):
    pomagma.util.check_call(
        os.path.join(pomagma.util.BIN, 'grower', pomagma.util.GROWERS[theory]),
        abspath(chart_in),
        abspath(chart_out),
        size=size,
        **opts)


def aggregate(atlas_in, chart_in, atlas_out, **opts):
    pomagma.util.check_call(
        os.path.join(pomagma.util.BIN, 'atlas', 'aggregate'),
        abspath(atlas_in),
        abspath(chart_in),
        abspath(atlas_out),
        **opts)


def copy(chart_in, chart_out, **opts):
    pomagma.util.check_call(
        os.path.join(pomagma.util.BIN, 'atlas', 'copy'),
        abspath(chart_in),
        abspath(chart_out),
        **opts)
