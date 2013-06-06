import os
import pomagma.util


def init(theory, chart_out, size=None, **opts):
    if size is None:
        size = pomagma.util.MIN_SIZES[theory]
    surveyor = pomagma.util.SURVEYORS[theory]
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'surveyor', surveyor),
        pomagma.util.abspath(chart_out),
        size=size,
        **opts)


def survey(theory, chart_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    surveyor = pomagma.util.SURVEYORS[theory]
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'surveyor', surveyor),
        pomagma.util.abspath(chart_in),
        pomagma.util.abspath(chart_out),
        size=size,
        **opts)
