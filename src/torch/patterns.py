import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import torch

from pomagma.compiler.expressions import Expression

if TYPE_CHECKING:
    from .language import Language
    from .structure import Structure

logger = logging.getLogger(__name__)


@dataclass
class PatternCandidate:
    """A subexpression that appears multiple times and could be abstracted."""

    pattern: Expression
    frequency: int
    locations: List[Tuple[int, List[int]]]  # (expr_index, path_to_subexpr)
    estimated_benefit: float  # Size reduction benefit (negative log prob difference)


def enumerate_subexpressions(
    expr: Expression, path: Optional[List[int]] = None
) -> List[Tuple[Expression, List[int]]]:
    """
    Enumerate all subexpressions of an expression with their paths.

    Args:
        expr: The expression to analyze
        path: Current path (for recursion)

    Returns:
        List of (subexpression, path) pairs
    """
    if path is None:
        path = []

    subexprs = [(expr, path)]

    for i, arg in enumerate(expr.args):
        arg_path = path + [i]
        subexprs.extend(enumerate_subexpressions(arg, arg_path))

    return subexprs


def find_common_patterns(
    expressions: List[Expression], min_frequency: int = 2, min_size: int = 2
) -> List[PatternCandidate]:
    """
    Find subexpressions that appear frequently across expressions.

    Args:
        expressions: List of expressions to analyze
        min_frequency: Minimum number of occurrences to consider
        min_size: Minimum expression size (number of nodes) to consider

    Returns:
        List of pattern candidates sorted by estimated benefit
    """
    # Count occurrences of each subexpression
    pattern_locations: Dict[Expression, List[Tuple[int, List[int]]]] = defaultdict(list)

    for expr_idx, expr in enumerate(expressions):
        subexprs = enumerate_subexpressions(expr)
        for subexpr, path in subexprs:
            # Filter by minimum size
            if _expression_size(subexpr) >= min_size:
                pattern_locations[subexpr].append((expr_idx, path))

    # Filter by frequency and create candidates
    candidates = []
    for pattern, locations in pattern_locations.items():
        if len(locations) >= min_frequency:
            candidate = PatternCandidate(
                pattern=pattern,
                frequency=len(locations),
                locations=locations,
                estimated_benefit=0.0,  # Will be computed later
            )
            candidates.append(candidate)

    logger.info(f"Found {len(candidates)} pattern candidates")
    return candidates


def estimate_compression_benefit(
    candidate: PatternCandidate,
    expressions: List[Expression],
    language: "Language",
    structure: "Structure",
    probs: torch.Tensor,
) -> float:
    """
    Estimate compression benefit for a pattern candidate using negative log probability.

    Args:
        candidate: The pattern candidate to evaluate
        expressions: Original expressions
        language: Language model for probability computation
        structure: E-graph structure (required)
        probs: Pre-computed E-class probabilities from language.compute_probs(structure)

    Returns:
        Estimated benefit (positive means compression is beneficial)
    """
    # Use proper complexity computation with negative log probability
    pattern_complexity = language.complexity(structure, probs, candidate.pattern)
    variable_complexity = 1.0  # Cost of a variable reference (arbitrary unit)

    # Benefit per occurrence = pattern complexity - variable complexity
    benefit_per_occurrence = pattern_complexity - variable_complexity

    # Total benefit = (benefit per occurrence * frequency) - abstraction cost
    # Abstraction cost is the complexity of creating the lambda abstraction
    # For now, use a simple estimate
    abstraction_cost = pattern_complexity + 2.0  # Pattern + lambda overhead

    total_benefit = (benefit_per_occurrence * candidate.frequency) - abstraction_cost

    return total_benefit


def _expression_size(expr: Expression) -> int:
    """Compute the size (number of nodes) of an expression."""
    return 1 + sum(_expression_size(arg) for arg in expr.args)
