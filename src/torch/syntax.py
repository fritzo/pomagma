import logging
from typing import Optional

# Import to register Expression.abstract() method via @methodof decorator
import pomagma.compiler.extensional  # noqa: F401
from pomagma.compiler.expressions import Expression

logger = logging.getLogger(__name__)


def replace_pattern_with_variable(
    expr: Expression, pattern: Expression, variable: Expression
) -> Expression:
    """
    Replace all occurrences of pattern with variable in expression.

    Args:
        expr: Expression to transform
        pattern: Pattern to replace
        variable: Variable to substitute

    Returns:
        Transformed expression
    """
    # Use the new Expression.replace() method
    return expr.replace(pattern, variable)


def create_curry_abstraction(
    pattern: Expression, variable_name: str = "x"
) -> Expression:
    """
    Create a Curry-style lambda abstraction for a pattern.

    Uses the abstraction algorithm from src/compiler/extensional.py.

    Args:
        pattern: Expression to abstract
        variable_name: Name for the bound variable

    Returns:
        Abstracted expression (closed term)
    """
    variable = Expression.make(variable_name)

    # Substitute the variable into the pattern, then abstract it out
    # This creates a lambda abstraction λx.pattern[x/variable_name]
    pattern_with_var = pattern.replace(Expression.make(variable_name), variable)

    # Call abstract as a method on the Expression object
    abstracted = pattern_with_var.abstract(variable)

    return abstracted


def apply_beta_eta_reduction(expr: Expression) -> Expression:
    """
    Apply beta-eta reduction to simplify an expression.

    Uses existing reduction logic from src/reducer modules.

    Args:
        expr: Expression to reduce

    Returns:
        Reduced expression
    """
    # TODO: Implement using existing src/reducer logic
    # For now, return unchanged as requested
    return expr


def generate_fresh_variable_name(existing_names: Optional[set] = None) -> str:
    """
    Generate a fresh variable name that doesn't conflict with existing names.

    Args:
        existing_names: Set of names to avoid (optional)

    Returns:
        Fresh variable name
    """
    if existing_names is None:
        existing_names = set()

    # Simple strategy: use single letters
    for name in "xyzabcdefghijklmnopqrstuvw":
        if name not in existing_names:
            return name

    # Fallback to numbered variables
    counter = 0
    while True:
        name = f"x{counter}"
        if name not in existing_names:
            return name
        counter += 1
