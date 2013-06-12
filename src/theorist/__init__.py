import os
import pomagma.util
import pomagma.theorist.diverge


def filter_diverge(conjectures_in, theorems_out, **opts):
    log_file = opts['log_file']
    pomagma.util.log_print('Filtering divergence conjectures', log_file)
    return pomagma.theorist.diverge.filter_diverge(
        conjectures_in,
        theorems_out)


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
