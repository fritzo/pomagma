import os
import pomagma.util


BIN = os.path.join(pomagma.util.BIN, 'analyst')


def simplify(theory, world, terms_in, terms_out, **opts):
    pomagma.util.log_call(
        os.path.join(BIN, 'simplify'),
        pomagma.util.abspath(world),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        pomagma.util.abspath(terms_in),
        pomagma.util.abspath(terms_out),
        **opts)


def serve(theory, world, **opts):
    pomagma.util.log_call(
        os.path.join(BIN, 'serve'),
        pomagma.util.abspath(world),
        os.path.join(pomagma.util.LANGUAGE, '{}.language'.format(theory)),
        **opts)
