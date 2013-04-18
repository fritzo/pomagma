'''
Wrapper for pomagma actions implemented in C++.
'''

import os
import pomagma.util


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def init(laws, chart_out, size=None, **opts):
    if size is None:
        size = pomagma.util.MIN_SIZES[laws]
    surveyor = pomagma.util.SURVEYORS[laws]
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'surveyor', surveyor),
        abspath(chart_out),
        size=size,
        **opts)


def survey(laws, chart_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[laws]:
        raise ValueError('chart is too small for laws')
    surveyor = pomagma.util.SURVEYORS[laws]
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'surveyor', surveyor),
        abspath(chart_in),
        abspath(chart_out),
        size=size,
        **opts)


def aggregate(world_in, region_in, world_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'aggregate'),
        abspath(world_in),
        abspath(region_in),
        abspath(world_out),
        **opts)


def trim(laws, world_in, region_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[laws]:
        raise ValueError('chart is too small for laws')
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'trim'),
        abspath(world_in),
        abspath(region_out),
        size,
        os.path.join(pomagma.util.LAWS, '{}.compiled'.format(laws)),
        os.path.join(pomagma.util.VEHICLES, '{}.vehicle'.format(laws)),
        **opts)


def copy(chart_in, chart_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'cartographer', 'copy'),
        abspath(chart_in),
        abspath(chart_out),
        **opts)


def engineer(chart_in, history_in, vehicle_in, vehicle_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'engineer', 'engineer'),
        abspath(chart_in),
        abspath(history_in),
        abspath(vehicle_in),
        abspath(vehicle_out),
        **opts)
