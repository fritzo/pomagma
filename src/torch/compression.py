import logging
from dataclasses import dataclass
from typing import Dict, List, Set

import torch

from pomagma.compiler.expressions import Expression

from .corpus import ObTree
from .extraction import Extractor
from .language import Language
from .patterns import (
    PatternCandidate,
    estimate_compression_benefit,
    find_common_patterns,
)
from .structure import Structure
from .syntax import (
    generate_fresh_variable_name,
    replace_pattern_with_variable,
)

logger = logging.getLogger(__name__)


@dataclass
class CompressionConfig:
    """Configuration for beta-compression algorithm."""

    min_pattern_frequency: int = 2
    min_pattern_size: int = 2
    max_iterations: int = 5
    compression_threshold: float = 0.1  # minimum relative benefit


@dataclass
class CompressionStats:
    """Statistics about compression results."""

    patterns_found: int
    abstractions_created: int
    original_total_size: int
    compressed_total_size: int
    compression_ratio: float


def beta_compress(
    structure: Structure,
    language: Language,
    probs: torch.Tensor,
    obtrees: List[ObTree],
    config: CompressionConfig = CompressionConfig(),
) -> Dict[Expression, float]:
    """
    Apply beta-compression to simplify a set of expressions.

    Algorithm:
    1. Extract expressions from ObTrees using enhanced extraction
    2. Find common subexpressions via pattern mining
    3. Create lambda abstractions for profitable patterns
    4. Apply syntactic reduction (beta-eta)
    5. Return equations between original and compressed forms with their benefits

    Args:
        structure: The E-graph structure
        language: PCFG for probability computation
        probs: Pre-computed E-class probabilities from language.compute_probs(structure)
        obtrees: List of expressions to compress (as ObTrees)
        config: Compression configuration

    Returns:
        Dict mapping EQUAL(original, compressed) equations to their compression benefits
    """
    logger.info(f"Starting beta-compression on {len(obtrees)} expressions")

    # Step 1: Extract expressions from ObTrees
    extractor = Extractor(structure, language)
    expressions = []
    for obtree in obtrees:
        expr = extractor.extract_from_obtree(obtree)
        if expr is not None:
            expressions.append(expr)

    if not expressions:
        logger.warning("No expressions could be extracted")
        return {}

    logger.info(f"Extracted {len(expressions)} expressions for compression")

    # Step 2: Iterative compression
    equation_benefits: Dict[Expression, float] = {}
    current_expressions = expressions[:]

    for iteration in range(config.max_iterations):
        logger.info(f"Compression iteration {iteration + 1}")

        # Find common patterns
        candidates = find_common_patterns(
            current_expressions,
            min_frequency=config.min_pattern_frequency,
            min_size=config.min_pattern_size,
        )

        if not candidates:
            logger.info("No more patterns found, stopping")
            break

        # Estimate benefits and select best candidate
        best_candidate = None
        best_benefit = 0.0

        for candidate in candidates:
            benefit = estimate_compression_benefit(
                candidate, current_expressions, language, structure, probs
            )
            if benefit > best_benefit:
                best_benefit = benefit
                best_candidate = candidate

        if best_candidate is None or best_benefit < config.compression_threshold:
            logger.info(f"No profitable patterns found (best benefit: {best_benefit})")
            break

        logger.info(
            f"Compressing pattern {best_candidate.pattern} "
            f"(frequency: {best_candidate.frequency}, benefit: {best_benefit})"
        )

        # Step 3: Create abstraction
        compressed_expressions = _apply_compression(
            current_expressions, best_candidate, config
        )

        # Step 4: Generate equations with benefits
        for original, compressed in zip(current_expressions, compressed_expressions):
            if original != compressed:
                equation = Expression.make("EQUAL", original, compressed)
                equation_benefits[equation] = best_benefit

        # Update for next iteration
        current_expressions = compressed_expressions

    logger.info(f"Compression complete, generated {len(equation_benefits)} equations")
    return equation_benefits


def _apply_compression(
    expressions: List[Expression],
    candidate: PatternCandidate,
    config: CompressionConfig,
) -> List[Expression]:
    """
    Apply compression by abstracting a pattern candidate.

    Args:
        expressions: List of expressions to transform
        candidate: Pattern to abstract
        config: Compression configuration

    Returns:
        List of transformed expressions
    """
    # Generate fresh variable name
    existing_names = _collect_existing_names(expressions)
    var_name = generate_fresh_variable_name(existing_names)

    # Create variable and abstraction
    variable = Expression.make(var_name)

    # Step 1: Replace pattern with variable in all expressions
    substituted_expressions = []
    for expr in expressions:
        substituted = replace_pattern_with_variable(expr, candidate.pattern, variable)
        substituted_expressions.append(substituted)

    # For each expression, replace pattern with variable and create abstraction
    # Step 2: Create lambda abstraction for the pattern
    # Step 3: Apply beta-eta reduction

    # For now, return the substituted expressions (reduction is stubbed)
    return substituted_expressions


def _collect_existing_names(expressions: List[Expression]) -> Set[str]:
    """Collect all existing names in expressions to avoid conflicts."""
    names = set()

    def collect_names(expr: Expression):
        names.add(expr.name)
        for arg in expr.args:
            collect_names(arg)

    for expr in expressions:
        collect_names(expr)

    return names
