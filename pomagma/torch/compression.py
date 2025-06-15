import functools
import logging
from collections import Counter
from collections.abc import Callable

import torch

from pomagma.compiler.expressions import Expression
from pomagma.util.metrics import COUNTERS

from .corpus import ObTree
from .extraction import Extractor
from .language import Language
from .structure import Ob, Structure
from .syntax import beta_compress_expr_pattern

logger = logging.getLogger(__name__)
counter = COUNTERS[__name__]


@torch.no_grad()
def find_best_pattern(
    structure: Structure, language: Language, probs: torch.Tensor, obtree: ObTree
) -> Ob | None:
    """
    Find the best pattern E-class in an obtree based on occurrence analysis.

    Patterns are ranked by (num_occurrences - 1) * pattern_complexity.

    Args:
        structure: The E-graph structure
        language: PCFG for complexity computation
        probs: Pre-computed E-class probabilities
        obtree: ObTree to analyze for patterns

    Returns:
        Best pattern E-class (Ob) or None if no good patterns found.
    """
    counter["find_best_pattern"] += 1
    data_tensor = obtree.materialize(structure)
    occurrences = language.compute_occurrences(structure, data_tensor, probs=probs)

    # Benefit is the number of consolidated occurrences times the complexity,
    # where complexity = -log(probability).
    approx_benefit = -torch.xlogy(occurrences - 1, probs)
    best_ob_idx = approx_benefit.argmax(dim=0)
    best_benefit = approx_benefit[best_ob_idx]

    if best_benefit.item() > 0:
        return Ob(int(best_ob_idx.item()))

    counter["find_best_pattern.no_pattern"] += 1
    return None


@torch.no_grad()
def extract_tilted(
    structure: Structure,
    language: Language,
    probs: torch.Tensor,
    obtree: ObTree,
    pattern_ob: Ob,
) -> Expression | None:
    """
    Extract expression with tilted language favoring pattern_ob.

    Uses "rule of three" - triples the probability mass of the pattern E-class.

    Args:
        structure: The E-graph structure
        language: Original language
        pattern_ob: E-class to favor in extraction
        obtree: ObTree to extract from

    Returns:
        Extracted expression or None if extraction fails
    """
    counter["extract_tilted"] += 1

    # Fork the language
    tilted_language = Language(
        nullary_functions=language.nullary_functions.clone(),
        injective_functions={
            k: v.clone() for k, v in language.injective_functions.items()
        },
        binary_functions={k: v.clone() for k, v in language.binary_functions.items()},
        symmetric_functions={
            k: v.clone() for k, v in language.symmetric_functions.items()
        },
    )

    # Apply "rule of three" tilting - triple the mass
    tilted_language.nullary_functions[pattern_ob] += 2.0 * probs[pattern_ob]
    tilted_language.normalize_()

    # Extract with tilted language
    extractor = Extractor(structure, tilted_language)
    return extractor.extract_from_obtree(obtree)


def beta_compress(
    structure: Structure,
    language: Language,
    probs: torch.Tensor,
    obtrees: list[ObTree],
) -> dict[Expression, float]:
    """
    Apply beta-compression to simplify a set of expressions.

    For each obtree:
    1. Find best pattern (E-class) via occurrence analysis
    2. Extract expression with tilted language favoring that pattern
    3. Apply beta_compress_expr_pattern to compress with the pattern
    4. Aggregate results

    Args:
        structure: The E-graph structure
        language: PCFG for probability computation
        probs: Pre-computed E-class probabilities from language.compute_probs(structure)
        obtrees: List of expressions to compress (as ObTrees)

    Returns:
        Dict mapping EQUAL(original, compressed) equations to their compression benefits
    """
    counter["beta_compress"] += 1
    equation_benefits: Counter[Expression] = Counter()
    cost_func = functools.partial(language.complexity, structure, probs)
    for i, obtree in enumerate(obtrees):
        benefits = beta_compress_obtree(structure, language, probs, obtree, cost_func)
        equation_benefits.update(benefits)
    counter["beta_compress.equations"] = len(equation_benefits)
    return dict(equation_benefits)


def beta_compress_obtree(
    structure: Structure,
    language: Language,
    probs: torch.Tensor,
    obtree: ObTree,
    cost_func: Callable[[Expression], float],
) -> dict[Expression, float]:
    """
    Apply beta-compression to simplify an obtree.
    """
    counter["beta_compress_obtree"] += 1
    # Find best pattern as E-class (Ob)
    pattern_ob = find_best_pattern(structure, language, probs, obtree)
    if pattern_ob is None:
        counter["beta_compress_obtree.no_pattern"] += 1
        return {}

    # Extract expression with tilted language favoring the pattern
    expr = extract_tilted(structure, language, probs, obtree, pattern_ob)
    if expr is None:
        counter["beta_compress_obtree.no_expr"] += 1
        return {}

    # Get the actual pattern expression for compression
    extractor = Extractor(structure, language)
    ob_to_expr = extractor.extract_all_obs()
    pattern_expr = ob_to_expr.get(pattern_ob)
    if pattern_expr is None:
        counter["beta_compress_obtree.no_pattern_expr"] += 1
        return {}

    # Apply beta compression for this (expression, pattern) pair
    counter["beta_compress_obtree.compress"] += 1
    return beta_compress_expr_pattern(expr, pattern_expr, cost_func)
