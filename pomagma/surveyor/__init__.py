import os

import pomagma.util

BIN = os.path.join(pomagma.util.BIN, "surveyor")


def init(theory, chart_out, size=None, **opts):
    if size is None:
        size = pomagma.util.MIN_SIZES[theory]
    pomagma.util.log_call(
        os.path.join(BIN, "init"),
        pomagma.util.ensure_abspath(chart_out),
        os.path.join(pomagma.util.THEORY, f"{theory}.symbols"),
        os.path.join(pomagma.util.THEORY, f"{theory}.facts"),
        os.path.join(pomagma.util.THEORY, f"{theory}.optimized.programs"),
        os.path.join(pomagma.util.LANGUAGE, f"{theory}.language"),
        size=size,
        **opts,
    )


def survey(theory, chart_in, chart_out, size, **opts):
    if size < pomagma.util.MIN_SIZES[theory]:
        raise ValueError("chart is too small for theory")
    pomagma.util.log_call(
        os.path.join(BIN, "survey"),
        pomagma.util.ensure_abspath(chart_in),
        pomagma.util.ensure_abspath(chart_out),
        os.path.join(pomagma.util.THEORY, f"{theory}.symbols"),
        os.path.join(pomagma.util.THEORY, f"{theory}.facts"),
        os.path.join(pomagma.util.THEORY, f"{theory}.optimized.programs"),
        os.path.join(pomagma.util.LANGUAGE, f"{theory}.language"),
        size=size,
        **opts,
    )
