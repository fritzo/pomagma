import os
import pomagma.util


def conjecture_equal(theory, world_in, conjectures_out, **opts):
    pomagma.util.log_call(
        os.path.join(pomagma.util.BIN, 'theorist', 'conjecture_equal'),
        pomagma.util.abspath(world_in),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.abspath(conjectures_out),
        **opts)
