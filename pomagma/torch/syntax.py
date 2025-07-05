from collections import Counter
from collections.abc import Callable
from weakref import WeakKeyDictionary

import pomagma.compiler.extensional  # noqa: F401
from pomagma.compiler.expressions import Expression

_COUNT_PATTERNS_CACHE: WeakKeyDictionary[
    Expression, WeakKeyDictionary[Expression, int]
] = WeakKeyDictionary()


def count_patterns(expr: Expression, pattern: Expression) -> int:
    """
    Count the number of occurrences of a pattern in an expression.
    """
    if expr not in _COUNT_PATTERNS_CACHE:
        _COUNT_PATTERNS_CACHE[expr] = WeakKeyDictionary()
    if pattern not in _COUNT_PATTERNS_CACHE[expr]:
        if expr is pattern:
            count = 1
        else:
            count = sum(count_patterns(arg, pattern) for arg in expr.args)
        _COUNT_PATTERNS_CACHE[expr][pattern] = count
    return _COUNT_PATTERNS_CACHE[expr][pattern]


def beta_compress_expr_pattern(
    expr: Expression,
    pattern: Expression,
    cost_func: Callable[[Expression], float],
) -> Counter[Expression]:
    """
    Compress an expression by internally abstracting a given pattern.

    Returns:
        Counter mapping equations to their compression benefits
    """
    # Use dynamic programming to find the best compression.
    count = count_patterns(expr, pattern)
    if count < 2:
        return Counter()

    var = Expression("pattern")

    def compress(old: Expression) -> tuple[Expression, float]:
        new = old.replace(pattern, var).abstract(var)
        new = simplify(new)
        equation = Expression("EQUAL", old, new)
        benefit = cost_func(old) - cost_func(new)
        return equation, benefit

    # Try compressing at the top level.
    result_self: Counter[Expression] = Counter()
    if sum(1 for arg in expr.args if count_patterns(arg, pattern) > 0) >= 2:
        equation, benefit = compress(expr)
        if benefit > 0:
            result_self[equation] += benefit  # type: ignore[assignment]
    benefit_self = sum(result_self.values())

    # Try compressing args.
    result_args: Counter[Expression] = Counter()
    for arg in expr.args:
        if count_patterns(arg, pattern) >= 2:
            equation, benefit = compress(arg)
            if benefit > 0:
                result_args[equation] += benefit  # type: ignore[assignment]
    benefit_args = sum(result_args.values())

    # Choose the best result.
    return result_self if benefit_self > benefit_args else result_args


def simplify(expr: Expression) -> Expression:
    """
    Simplify an expression.
    """
    # TODO convert to lambda calculus and back, performing eager affine reduction
    return expr
