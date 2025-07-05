import logging
from typing import TYPE_CHECKING

import torch

from pomagma.compiler.expressions import Expression

from .corpus import ObTree
from .structure import Ob, Structure

if TYPE_CHECKING:
    from .language import Language

logger = logging.getLogger(__name__)


class Extractor:
    """Handles extraction of expressions from E-graphs and ObTrees."""

    def __init__(self, structure: Structure, language: "Language"):
        self.structure = structure
        self.language = language
        self._ob_to_expr_cache: dict[Ob, Expression | None] | None = None

    def extract_all_obs(
        self, *, best: torch.Tensor | None = None
    ) -> dict[Ob, Expression | None]:
        """
        Extracts the shortest expression for each E-class.
        Moved from Language.extract_all().
        """
        if self._ob_to_expr_cache is not None:
            return self._ob_to_expr_cache

        if best is None:
            best = self.language.compute_best(self.structure)
        assert best.shape == (1 + self.structure.item_count,)

        # Sort from highest to lowest probability, a valid topological order.
        order: list[Ob] = list(map(Ob, range(1, 1 + self.structure.item_count)))
        order.sort(key=lambda i: best[i].item(), reverse=True)

        # Index nullary functions by ob.
        nullary_functions: dict[Ob, str] = {
            ob: name for name, ob in self.structure.nullary_functions.items()
        }

        # Extract the shortest expression for each E-class.
        expressions: dict[Ob, Expression | None] = {Ob(0): None}
        for ob in order:
            # Skip if this object has zero probability
            if best[ob].item() <= 0:
                expressions[ob] = None
                continue

            # Find the best grammar rule to apply.
            best_prob: float = 0.0
            best_expr: Expression | None = None

            # Nullary functions.
            if ob in nullary_functions:
                prob = self.language.nullary_functions[ob].item()
                if prob > best_prob:
                    best_prob = prob
                    name = nullary_functions[ob]
                    best_expr = Expression(name)

            # Binary functions.
            for self_fs, struct_fs in [
                (self.language.binary_functions, self.structure.binary_functions),
                (self.language.symmetric_functions, self.structure.symmetric_functions),
            ]:
                for name, weight in self_fs.items():
                    Vlr = struct_fs[name].Vlr
                    begin = int(Vlr.ptrs[ob].item())
                    end = int(Vlr.ptrs[ob + 1].item())
                    if begin == end:
                        continue
                    # Get all (lhs, rhs) pairs that produce ob
                    lhs_rhs_pairs = Vlr.args[begin:end]  # Shape: [num_pairs, 2]
                    if lhs_rhs_pairs.numel() == 0:
                        continue
                    lhs_obs = lhs_rhs_pairs[:, 0]
                    rhs_obs = lhs_rhs_pairs[:, 1]
                    lhs_probs = best[lhs_obs.long()]
                    rhs_probs = best[rhs_obs.long()]
                    part_probs = weight.item() * lhs_probs * rhs_probs
                    max_value, max_idx = part_probs.max(dim=0)
                    value = max_value.item()
                    index = max_idx.item()
                    if value <= best_prob:
                        continue
                    # Get subexpressions (guaranteed to exist due to topological order)
                    lhs_ob = int(lhs_obs[index].item())
                    rhs_ob = int(rhs_obs[index].item())
                    lhs_expr = expressions.get(Ob(lhs_ob))
                    rhs_expr = expressions.get(Ob(rhs_ob))
                    if lhs_expr is None or rhs_expr is None:
                        continue
                    best_prob = value
                    best_expr = Expression(name, lhs_expr, rhs_expr)

            expressions[ob] = best_expr

        # Cache and return
        self._ob_to_expr_cache = expressions

        # Check that all expressions were successfully extracted.
        extracted_count = sum(
            1 for ob, e in expressions.items() if e is not None and ob != Ob(0)
        )
        logger.info("Extracted %s/%s obs", extracted_count, self.structure.item_count)
        expected_count = (best[1:] > 0).long().sum().item()
        assert extracted_count == expected_count

        return expressions

    def extract_from_obtree(self, obtree: ObTree) -> Expression | None:
        """
        Extract full expression from ObTree, combining E-class extraction with
        ObTree traversal.

        For ObTree leaves (ob != None): use extract_all_obs()
        For ObTree internal nodes: recursively extract args and build Expression
        """
        if obtree.ob is not None:
            # This is a leaf - extract from E-class
            ob_expressions = self.extract_all_obs()
            return ob_expressions.get(obtree.ob)

        # This is an internal node - recursively extract arguments
        if obtree.name is None or obtree.args is None:
            return None

        extracted_args = []
        for arg in obtree.args:
            extracted_arg = self.extract_from_obtree(arg)
            if extracted_arg is None:
                return None
            extracted_args.append(extracted_arg)

        return Expression(obtree.name, *extracted_args)
