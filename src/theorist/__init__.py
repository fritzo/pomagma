import os
import pomagma.util
from pomagma.theorist.diverge import filter_diverge


def conjecture_equal(theory, world_in, conjectures_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'theorist', 'conjecture_equal'),
        pomagma.util.abspath(world_in),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.abspath(conjectures_out),
        **opts)


def conjecture_diverge(theory, world_in, conjectures_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'theorist', 'conjecture_diverge'),
        pomagma.util.abspath(world_in),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.abspath(conjectures_out),
        **opts)


def assume(world_in, world_out, theory_in, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'theorist', 'assume'),
        pomagma.util.abspath(world_in),
        pomagma.util.abspath(world_out),
        pomagma.util.abspath(theory_in),
        **opts)
