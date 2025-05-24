#!/usr/bin/env python

from pomagma.reducer import bohm  # isort:skip
from pomagma.compiler.util import temp_memoize  # isort:skip
import os

os.environ['POMAGMA_LOG_LEVEL'] = '3'


print('Example 1.')
with temp_memoize():
    bohm.sexpr_simplify('(ABS (ABS (1 0 (1 0))) (ABS (ABS (1 (0 0)))))')


print('Example 2.')
with temp_memoize():
    bohm.sexpr_simplify('(ABS (ABS (0 1 1)) (ABS (ABS (1 (0 0)))))')
