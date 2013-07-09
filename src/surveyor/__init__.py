import os
import pomagma.util


BIN = os.path.join(pomagma.util.BIN, 'surveyor')


def init(theory, chart_out, size=None, **opts):
    if size is None:
        size = pomagma.util.MIN_SIZES[theory]
    initializer = os.path.join(BIN, '{}.init'.format(theory))
    pomagma.util.log_call(
        initializer,
        pomagma.util.abspath(chart_out),
        os.path.join(pomagma.util.THEORY, '{}.compiled'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.CPU_COUNT,
        size=size,
        **opts)


def survey(theory, chart_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    surveyor = os.path.join(BIN, '{}.survey'.format(theory))
    pomagma.util.log_call(
        surveyor,
        pomagma.util.abspath(chart_in),
        pomagma.util.abspath(chart_out),
        os.path.join(pomagma.util.THEORY, '{}.compiled'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.CPU_COUNT,
        size=size,
        **opts)
