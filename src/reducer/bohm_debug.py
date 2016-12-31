#!/usr/bin/env python

import os

os.environ['POMAGMA_LOG_LEVEL'] = '3'

from pomagma.compiler.util import MEMOIZED_CACHES  # isort:skip
from pomagma.reducer import bohm  # isort:skip


BASE = MEMOIZED_CACHES.copy()


def reset():
    for fun, cache in MEMOIZED_CACHES.iteritems():
        cache.clear()
        cache.update(BASE.get(fun, {}))


print('Example 1.')
bohm.sexpr_simplify('(ABS (ABS (1 0 (1 0))) (ABS (ABS (1 (0 0)))))')

reset()

print('Example 2.')
bohm.sexpr_simplify('(ABS (ABS (0 1 1)) (ABS (ABS (1 (0 0)))))')
