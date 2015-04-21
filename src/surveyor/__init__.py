import os
import pomagma.util


BIN = os.path.join(pomagma.util.BIN, 'surveyor')
USE_VM = int(os.environ.get('POMAGMA_USE_VM', 0))


def init(theory, chart_out, size=None, **opts):
    if size is None:
        size = pomagma.util.MIN_SIZES[theory]
    pomagma.util.log_call(
        os.path.join(BIN, 'init' if USE_VM else '{}.init'.format(theory)),
        pomagma.util.ensure_abspath(chart_out),
        os.path.join(pomagma.util.THEORY, '{}.symbols'.format(theory)),
        os.path.join(pomagma.util.THEORY, '{}.facts'.format(theory)),
        os.path.join(pomagma.util.THEORY, '{}.programs'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.CPU_COUNT,
        size=size,
        **opts)


def survey(theory, chart_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError('chart is too small for theory')
    pomagma.util.log_call(
        os.path.join(BIN, 'survey' if USE_VM else '{}.survey'.format(theory)),
        pomagma.util.ensure_abspath(chart_in),
        pomagma.util.ensure_abspath(chart_out),
        os.path.join(pomagma.util.THEORY, '{}.symbols'.format(theory)),
        os.path.join(pomagma.util.THEORY, '{}.facts'.format(theory)),
        os.path.join(pomagma.util.THEORY, '{}.programs'.format(theory)),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.CPU_COUNT,
        size=size,
        **opts)
