import logging
import math
from collections.abc import Mapping, Sequence

import torch
from immutables import Map

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr

from .corpus import CorpusStats, ObTree
from .structure import Structure

logger = logging.getLogger(__name__)

EMPTY_MAP: Mapping[str, torch.Tensor] = Map()


class Language(torch.nn.Module):
    """
    PyTorch representation of a probabilistic grammar.

    Nullary functions are materialized as a dense tensor wrt a Structure.
    All other data are merely scalar weights.

    Note this data structure is agnostic to weight semantics: weights can denote
    a probabilistic generator, or observation counts, or log-probabilities, etc.
    """

    def __init__(
        self,
        *,
        nullary_functions: torch.Tensor,
        injective_functions: Mapping[str, torch.Tensor] = EMPTY_MAP,
        binary_functions: Mapping[str, torch.Tensor] = EMPTY_MAP,
        symmetric_functions: Mapping[str, torch.Tensor] = EMPTY_MAP,
    ) -> None:
        super().__init__()
        self.nullary_functions = torch.nn.Parameter(nullary_functions)
        self.injective_functions = torch.nn.ParameterDict(
            {
                name: torch.nn.Parameter(weight)
                for name, weight in injective_functions.items()
            }
        )
        self.binary_functions = torch.nn.ParameterDict(
            {
                name: torch.nn.Parameter(weight)
                for name, weight in binary_functions.items()
            }
        )
        self.symmetric_functions = torch.nn.ParameterDict(
            {
                name: torch.nn.Parameter(weight)
                for name, weight in symmetric_functions.items()
            }
        )

    def total(self) -> torch.Tensor:
        result: torch.Tensor = self.nullary_functions.sum()
        for _, weight in sorted(self.injective_functions.items()):
            result += weight
        for _, weight in sorted(self.binary_functions.items()):
            result += weight
        for _, weight in sorted(self.symmetric_functions.items()):
            result += weight
        return result

    @torch.no_grad()
    def normalize_(self) -> None:
        scale: torch.Tensor = 1.0 / self.total()
        self.nullary_functions *= scale
        for _, weight in sorted(self.injective_functions.items()):
            weight *= scale
        for _, weight in sorted(self.binary_functions.items()):
            weight *= scale
        for _, weight in sorted(self.symmetric_functions.items()):
            weight *= scale

    @torch.no_grad()
    def project_to_feasible_(self) -> None:
        """Project parameters to feasible set: nonnegativity + normalization."""
        # Ensure nonnegativity
        self.nullary_functions.clamp_(min=0.0)
        for weight in self.injective_functions.values():
            weight.clamp_(min=0.0)
        for weight in self.binary_functions.values():
            weight.clamp_(min=0.0)
        for weight in self.symmetric_functions.values():
            weight.clamp_(min=0.0)

        # Renormalize
        self.normalize_()

    def compute_probs(
        self,
        structure: Structure,
        *,
        reltol: float = 1e-3,
        init_probs: torch.Tensor | None = None,
        min_steps: int = 5,
    ) -> torch.Tensor:
        """
        Propagates from a normalized grammar to a sub-normalized weighted set of obs.

        (The ob set would be normalized if the structure were closed, but the
        structure is only a finite subset of the full structure.)

        Args:
            structure: The E-graph structure
            reltol: Relative tolerance for convergence
            init_probs: Optional warm start initialization
            min_steps: Minimum steps to run even if converged (for gradient quality)
        """
        assert 0.0 < reltol < 1.0
        assert min_steps >= 0
        eps = torch.finfo(self.nullary_functions.dtype).eps

        # Initialize with warm start if provided, else atoms.
        if init_probs is None:
            probs = self.nullary_functions.detach()
        else:
            probs = init_probs.clone()

        # Propagate until convergence (with minimum steps).
        diff = 1.0
        step = 0
        while diff > reltol or step < min_steps:
            prev = probs
            probs = self._compute_probs_step(structure, probs)
            with torch.no_grad():
                # Only the convergence check is in no_grad - doesn't affect gradients
                diffs = (probs - prev).abs() / (probs + eps)
                diff = diffs.max().item()
            step += 1

        return probs

    @torch.no_grad()
    def compute_best(
        self, structure: Structure, *, reltol: float = 1e-3
    ) -> torch.Tensor:
        """
        Propagates from a normalized grammar to find the best (max probability)
        path to each ob.

        Unlike compute_probs which sums over all derivations, this finds the single
        highest-probability derivation for each E-class for E-graph extraction.
        """
        assert 0.0 < reltol < 1.0
        eps = torch.finfo(self.nullary_functions.dtype).eps

        # Initialize with atoms.
        best = self.nullary_functions.detach()

        # Propagate until convergence.
        diff = 1.0
        while diff > reltol:
            prev = best
            best = self._compute_best_step(structure, best)
            diffs = (best - prev).abs() / (best + eps)
            diff = diffs.max().item()

        return best

    def _compute_probs_step(
        self, structure: Structure, probs: torch.Tensor
    ) -> torch.Tensor:
        # Propagates mass from subexpressions to their super-expressions.
        out = self.nullary_functions.clone()
        for name, weight in self.binary_functions.items():
            fn = structure.binary_functions[name]
            out += weight * fn.sum_product(probs, probs)
        for name, weight in self.symmetric_functions.items():
            fn = structure.symmetric_functions[name]
            out += weight * fn.sum_product(probs, probs)
        return out

    def _compute_best_step(
        self, structure: Structure, best: torch.Tensor
    ) -> torch.Tensor:
        # Propagates max probability from subexpressions to their super-expressions.
        out = self.nullary_functions.clone()
        for name, weight in self.binary_functions.items():
            fn = structure.binary_functions[name]
            out = torch.maximum(out, weight * fn.max_product(best, best))
        for name, weight in self.symmetric_functions.items():
            fn = structure.symmetric_functions[name]
            out = torch.maximum(out, weight * fn.max_product(best, best))
        return out

    def _compute_occurrences_step(
        self,
        structure: Structure,
        counts: torch.Tensor,
        probs: torch.Tensor,
        data: torch.Tensor,
    ) -> torch.Tensor:
        # Propagates counts from super-expressions to their sub-expressions.
        # Start with the original data (baseline occurrences)
        new_counts = data.clone()
        for name, weight in self.binary_functions.items():
            fn = structure.binary_functions[name]
            child_contributions = fn.distribute_product(counts, probs, weight.item())
            new_counts += child_contributions
        for name, weight in self.symmetric_functions.items():
            fn = structure.symmetric_functions[name]
            child_contributions = fn.distribute_product(counts, probs, weight.item())
            new_counts += child_contributions
        return new_counts

    def compute_rules(
        self, structure: Structure, data: torch.Tensor, *, reltol=1e-3
    ) -> torch.Tensor:
        """
        Counts the effective number of uses of each grammar production rule in
        the data, averaged over extractions.
        """
        # This uses Eisner's gradient trick: the gradient of log P(data | probs)
        # with respect to grammar parameters gives the expected count of each
        # grammar rule/E-class.
        assert data.shape == self.nullary_functions.shape
        assert 0.0 < reltol < 1.0
        tiny = torch.finfo(self.nullary_functions.dtype).tiny

        # Compute the "inside" probabilities with gradient tracking
        self.nullary_functions.requires_grad_(True)
        probs = self.compute_probs(structure, reltol=reltol)

        # Compute log-probability of observed data under the probability distribution
        # log P(data | probs) = ∑_i data[i] * log(probs[i])
        log_likelihood = torch.xlogy(data, probs + tiny).sum()

        # Apply Eisner's gradient trick: ∂/∂params log P(data | params) = E[counts]
        # The gradient automatically propagates through the E-graph structure
        inputs: list[torch.Tensor] = [
            self.nullary_functions,
            *self.injective_functions.values(),
            *self.binary_functions.values(),
            *self.symmetric_functions.values(),
        ]
        grads: Sequence[torch.Tensor] = torch.autograd.grad(
            outputs=log_likelihood,
            inputs=inputs,
            create_graph=False,
            retain_graph=False,
            only_inputs=True,
        )

        # Scale the gradients and collate into a Language.
        grads = list(reversed(grads))
        with torch.no_grad():
            nullary_functions = grads.pop() * self.nullary_functions
            injective_functions = {
                name: grads.pop() * weight
                for name, weight in self.injective_functions.items()
            }
            binary_functions = {
                name: grads.pop() * weight
                for name, weight in self.binary_functions.items()
            }
            symmetric_functions = {
                name: grads.pop() * weight
                for name, weight in self.symmetric_functions.items()
            }
        return Language(
            nullary_functions=nullary_functions,
            injective_functions=injective_functions,
            binary_functions=binary_functions,
            symmetric_functions=symmetric_functions,
        )

    @torch.no_grad()
    def compute_occurrences(
        self,
        structure: Structure,
        data: torch.Tensor,
        *,
        probs: torch.Tensor | None = None,
        reltol: float = 1e-3,
    ) -> torch.Tensor:
        """
        Counts the number of occurrences of each subexpression of each E-class in
        expressions from a corpus. This includes both leaf nodes (from grammar rules)
        and internal node E-classes.
        """
        # This uses backward propagation from observed data through the E-graph
        # structure, distributing occurrence counts based on
        # probability-weighted decompositions.
        assert data.shape == self.nullary_functions.shape
        assert 0.0 < reltol < 1.0
        eps = torch.finfo(self.nullary_functions.dtype).eps
        if probs is None:
            # Compute the forward probabilities once
            probs = self.compute_probs(structure, reltol=reltol)

        # Initialize with the observed data - these are the "root" occurrences
        counts = data.clone()

        # Propagate until convergence
        diff = 1.0
        while diff > reltol:
            prev = counts
            counts = self._compute_occurrences_step(structure, counts, probs, data)
            diffs = (counts - prev).abs() / (counts + eps)
            diff = diffs.max().item()

        return counts

    def log_prob(
        self,
        structure: Structure,
        generator: "Language",
        probs: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """
        Compute the log probability of corpus data (self) under a generator PCFG.

        This method computes the total log-likelihood of the corpus represented by
        `self` under the probability distribution defined by `generator`. The corpus
        should have been created via `Language.zeros_like()` + `Language.iadd_corpus()`
        from an ObTree.

        The log-likelihood has two components:
        1. E-class probabilities: For each E-class, sum(corpus_count[i] * log(prob[i]))
           where corpus_count comes from self.nullary_functions and prob comes from
           generator.compute_probs(structure).
        2. Function weights: For each function symbol,
           sum(corpus_count[f] * log(weight[f])) where corpus_count comes from
           self.binary_functions etc. and weight comes from generator's
           corresponding function weights.

        Args:
            structure: The E-graph structure for computing E-class probabilities
            generator: The PCFG Language model from which to compute probabilities
            probs: Optional pre-computed E-class probabilities from generator.
                  If None, will compute via generator.compute_probs(structure).

        Returns:
            Total log-likelihood of the corpus under the generator
        """
        if probs is None:
            probs = generator.compute_probs(structure)

        tiny = torch.finfo(probs.dtype).tiny

        # E-class probability contributions
        log_likelihood = torch.xlogy(self.nullary_functions, probs + tiny).sum()

        # Function weight contributions
        for name, corpus_count in self.injective_functions.items():
            generator_weight = generator.injective_functions[name]
            log_likelihood += torch.xlogy(corpus_count, generator_weight + tiny)
        for name, corpus_count in self.binary_functions.items():
            generator_weight = generator.binary_functions[name]
            log_likelihood += torch.xlogy(corpus_count, generator_weight + tiny)
        for name, corpus_count in self.symmetric_functions.items():
            generator_weight = generator.symmetric_functions[name]
            log_likelihood += torch.xlogy(corpus_count, generator_weight + tiny)

        return log_likelihood

    def zeros_like(self) -> "Language":
        """
        Returns a new language with the same structure but all weights zero.
        """
        return Language(
            nullary_functions=torch.zeros_like(self.nullary_functions),
            injective_functions=Map(
                {k: torch.zeros_like(v) for k, v in self.injective_functions.items()}
            ),
            binary_functions=Map(
                {k: torch.zeros_like(v) for k, v in self.binary_functions.items()}
            ),
            symmetric_functions=Map(
                {k: torch.zeros_like(v) for k, v in self.symmetric_functions.items()}
            ),
        )

    def clone(self) -> "Language":
        """
        Returns a deep copy of the language with the same structure and weights.
        """
        return Language(
            nullary_functions=self.nullary_functions.clone().detach(),
            injective_functions=Map(
                {k: v.clone().detach() for k, v in self.injective_functions.items()}
            ),
            binary_functions=Map(
                {k: v.clone().detach() for k, v in self.binary_functions.items()}
            ),
            symmetric_functions=Map(
                {k: v.clone().detach() for k, v in self.symmetric_functions.items()}
            ),
        )

    @torch.no_grad()
    def iadd_corpus(self, corpus_stats: CorpusStats, weight: float = 1.0) -> None:
        """
        Adds data weights from a corpus, in-place.
        """
        # Add counts to language
        for ob, count in corpus_stats.obs.items():
            self.nullary_functions[ob] += count * weight
        for name, count in corpus_stats.symbols.items():
            if name in self.injective_functions:
                self.injective_functions[name] += count * weight
            elif name in self.binary_functions:
                self.binary_functions[name] += count * weight
            elif name in self.symmetric_functions:
                self.symmetric_functions[name] += count * weight
            else:
                raise ValueError(f"Unknown symbol: {name}")

    def extract_all(
        self, structure: Structure, *, best: torch.Tensor | None = None
    ) -> list[Expression | None]:
        """
        Extracts the shortest expression for each E-class.
        Delegates to Extractor for the actual implementation.
        """
        from .extraction import Extractor

        extractor = Extractor(structure, self)
        ob_to_expr = extractor.extract_all_obs(best=best)

        # Convert to list format for backward compatibility
        expressions: list[Expression | None] = [None] * (1 + structure.item_count)
        for ob, expr in ob_to_expr.items():
            expressions[ob] = expr

        return expressions

    def compute_expression_size(
        self,
        structure: Structure,
        expr: Expression,
        *,
        probs: torch.Tensor | None = None,
    ) -> float:
        """
        Compute expression size as negative log probability.

        This provides a principled size metric for compression decisions.

        Args:
            structure: The E-graph structure
            expr: Expression to measure
            probs: Pre-computed probabilities (optional)

        Returns:
            Negative log probability (higher = larger/more complex)
        """

        # TODO: Implement proper negative log probability computation
        # For now, use a simple tree size heuristic
        def tree_size(e: Expression) -> int:
            return 1 + sum(tree_size(arg) for arg in e.args)

        size = tree_size(expr)
        # Convert to negative log probability scale (larger size = higher cost)
        return float(size)  # Placeholder - should be -log(P(expr))

    def complexity(
        self,
        structure: Structure,
        probs: torch.Tensor,
        x: CorpusStats | ObTree | Expression | str,
    ) -> float:
        """
        Compute complexity as negative log probability.

        This unified method handles multiple input types and computes complexity
        using corpus statistics, taking into account both symbol costs and
        E-class probabilities.

        Args:
            structure: The E-graph structure
            probs: Pre-computed E-class probabilities from language.compute_probs
            x: Input to measure complexity of - can be:
                - str: Parsed to Expression
                - Expression: Converted to ObTree
                - ObTree: Converted to CorpusStats
                - CorpusStats: Used directly

        Returns:
            Negative log probability (higher = more complex)
        """
        # Convert input through the transformation chain
        if isinstance(x, str):
            x = parse_string_to_expr(x)
        if isinstance(x, Expression):
            x = ObTree.from_expr(structure, x)
        if isinstance(x, ObTree):
            x = x.stats
        assert isinstance(x, CorpusStats), f"Expected CorpusStats, got {type(x)}"

        # Now compute complexity using corpus stats
        total_cost = 0.0

        # Cost from E-class occurrences (negative log probability)
        for ob, count in x.obs.items():
            prob = probs[ob].item()
            if prob <= 0:
                return float("inf")  # Impossible expression
            total_cost += count * (-math.log(prob))

        # Cost from symbol occurrences (negative log probability)
        for symbol, count in x.symbols.items():
            symbol_cost = 0.0
            if symbol in self.injective_functions:
                weight = self.injective_functions[symbol].item()
                if weight <= 0:
                    return float("inf")
                symbol_cost = -math.log(weight)
            elif symbol in self.binary_functions:
                weight = self.binary_functions[symbol].item()
                if weight <= 0:
                    return float("inf")
                symbol_cost = -math.log(weight)
            elif symbol in self.symmetric_functions:
                weight = self.symmetric_functions[symbol].item()
                if weight <= 0:
                    return float("inf")
                symbol_cost = -math.log(weight)
            else:
                # Unknown symbol - assign high cost
                symbol_cost = 10.0  # Arbitrary high cost

            total_cost += count * symbol_cost

        return total_cost

    def obtree_complexity(
        self, structure: Structure, probs: torch.Tensor, tree: "ObTree"
    ) -> float:
        """
        DEPRECATED: Use complexity() instead.
        Compute complexity of an ObTree as negative log probability.
        """
        return self.complexity(structure, probs, tree)

    def expr_complexity(
        self, structure: Structure, probs: torch.Tensor, expr: Expression
    ) -> float:
        """
        DEPRECATED: Use complexity() instead.
        Compute expression complexity as negative log probability.
        """
        return self.complexity(structure, probs, expr)

    def fit(
        self,
        structure: Structure,
        corpus_stats: CorpusStats,
        *,
        max_steps: int = 50,
        learning_rate: float = 0.1,
        tol: float = 1e-6,
        reltol: float = 1e-4,
    ) -> list[float]:
        """
        Fit language weights to a corpus using L-BFGS.

        Args:
            structure: The E-graph structure
            corpus_stats: Training corpus statistics (CorpusStats)
            max_steps: Maximum optimization steps
            learning_rate: Learning rate for L-BFGS
            tol: Tolerance for optimization convergence
            reltol: Relative tolerance for compute_probs iterations

        Returns:
            List of losses
        """
        # Create a Language with the same structure as self to hold corpus counts
        corpus_language = self.zeros_like()
        corpus_language.iadd_corpus(corpus_stats)
        corpus_size = int(corpus_language.nullary_functions.sum().item())

        # Track metrics
        losses: list[float] = []
        logger.info("Fitting to corpus of size %s", corpus_size)

        # Setup optimizer
        optimizer = torch.optim.LBFGS(
            self.parameters(),
            lr=learning_rate,
            max_iter=20,
            tolerance_grad=tol,
            tolerance_change=tol,
            history_size=10,
        )

        # Warm start for compute_probs
        prev_probs = None

        def closure():
            nonlocal prev_probs
            optimizer.zero_grad()

            # Compute probabilities with warm start
            probs = self.compute_probs(
                structure, reltol=reltol, init_probs=prev_probs, min_steps=3
            )
            prev_probs = probs.detach()

            # Compute loss as negative log-likelihood
            loss = -corpus_language.log_prob(structure, self, probs)
            loss.backward()
            return loss

        # Optimization loop
        for step in range(max_steps):
            loss = optimizer.step(closure)
            self.project_to_feasible_()
            losses.append(loss.item())
            if step % 10 == 0 or step == max_steps - 1:
                logger.info("Step %s: loss=%.6f", step, loss.item())

        return losses
