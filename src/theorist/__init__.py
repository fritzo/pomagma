import os
import pomagma.util
import pomagma.theorist.diverge


BIN = os.path.join(pomagma.util.BIN, 'theorist')


def _count_facts(filename):
    count = 0
    if os.path.exists(filename):
        with open(filename) as f:
            for line in f:
                if line.split('#', 1)[0].strip():
                    count += 1
    return count


def try_prove_nless(
        theory,
        world_in,
        conjectures_in,
        conjectures_out,
        theorems_out,
        **opts):
    prev_theorem_count = _count_facts(theorems_out)
    pomagma.util.log_call(
        os.path.join(BIN, 'try_prove_nless'),
        pomagma.util.abspath(world_in),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.abspath(conjectures_in),
        pomagma.util.abspath(conjectures_out),
        pomagma.util.abspath(theorems_out),
        **opts)
    theorem_count = _count_facts(theorems_out) - prev_theorem_count
    return theorem_count


def try_prove_diverge(conjectures_in, conjectures_out, theorems_out, **opts):
    theorem_count = pomagma.theorist.diverge.try_prove_diverge(
        pomagma.util.abspath(conjectures_in),
        pomagma.util.abspath(conjectures_out),
        pomagma.util.abspath(theorems_out),
        **opts)
    return theorem_count
