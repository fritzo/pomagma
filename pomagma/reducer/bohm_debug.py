#!/usr/bin/env python
import os

os.environ["POMAGMA_LOG_LEVEL"] = "3"

# isort: split

from pomagma.compiler.util import temp_memoize
from pomagma.reducer import bohm

print("Example 1.")
with temp_memoize():
    bohm.sexpr_simplify("(ABS (ABS (1 0 (1 0))) (ABS (ABS (1 (0 0)))))")


print("Example 2.")
with temp_memoize():
    bohm.sexpr_simplify("(ABS (ABS (0 1 1)) (ABS (ABS (1 (0 0)))))")
