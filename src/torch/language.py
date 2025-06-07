import logging
import math
from collections import Counter
from typing import Any, Mapping, Sequence

import torch
from immutables import Map

from pomagma.compiler.expressions import Expression

from .corpus import ObTree
from .structure import Ob, Structure

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

    def compute_probs(
        self,
        structure: Structure,
        *,
        reltol: float = 1e-3,
        init_probs: torch.Tensor | None = None,
        min_iterations: int = 3,
    ) -> torch.Tensor:
        """
        Propagates from a normalized grammar to a sub-normalized weighted set of obs.

        (The ob set would be normalized if the structure were closed, but the
        structure is only a finite subset of the full structure.)

        Args:
            structure: The E-graph structure
            reltol: Relative tolerance for convergence
            init_probs: Optional warm start initialization
            min_iterations: Minimum iterations to run even if converged
                (for gradient quality)
        """
        assert 0.0 < reltol < 1.0
        assert min_iterations >= 0
        eps = torch.finfo(self.nullary_functions.dtype).eps

        # Initialize with warm start if provided, else atoms.
        if init_probs is not None:
            probs = init_probs.clone()
        else:
            probs = self.nullary_functions.detach()

        # Propagate until convergence (with minimum iterations).
        diff = 1.0
        iteration = 0
        while diff > reltol or iteration < min_iterations:
            prev = probs
            probs = self._compute_probs_step(structure, probs)
            with torch.no_grad():
                # Only the convergence check is in no_grad - doesn't affect gradients
                diffs = (probs - prev).abs() / (probs + eps)
                diff = diffs.max().item()
            iteration += 1

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

    def log_prob(self, generator: "Language", probs: torch.Tensor) -> torch.Tensor:
        """
        Compute the log probability of data under propagated probabilities.
        """
        h = torch.nn.functional.cross_entropy(
            self.nullary_functions, probs, reduction="sum"
        )
        ws: list[torch.Tensor] = []
        ps: list[torch.Tensor] = []
        for name, weight in self.injective_functions.items():
            ws.append(weight)
            ps.append(generator.injective_functions[name])
        for name, weight in self.binary_functions.items():
            ws.append(weight)
            ps.append(generator.binary_functions[name])
        for name, weight in self.symmetric_functions.items():
            ws.append(weight)
            ps.append(generator.symmetric_functions[name])
        if ws:
            h += torch.nn.functional.cross_entropy(
                torch.stack(ws), torch.stack(ps), reduction="sum"
            )
        return -h

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

    def iadd_corpus(self, ob_tree: ObTree, weight: float = 1.0) -> None:
        """
        Adds data weights from a corpus, in-place.
        """
        # Count symbols and objects
        symbol_counts: Counter[str] = Counter()
        ob_counts: Counter[Ob] = Counter()
        ob_tree.count(symbol_counts, ob_counts)

        # Add counts to language
        for ob, count in ob_counts.items():
            self.nullary_functions[ob] += count * weight
        for name, count in symbol_counts.items():
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
        """
        if best is None:
            best = self.compute_best(structure)
        assert best.shape == (1 + structure.item_count,)

        # Sort from highest to lowest probability, a valid topological order.
        order: list[Ob] = list(map(Ob, range(1, 1 + structure.item_count)))
        order.sort(key=lambda i: best[i].item(), reverse=True)

        # Index nullary functions by ob.
        nullary_functions: dict[Ob, str] = {}
        for name, ob in structure.nullary_functions.items():
            nullary_functions[ob] = name

        # Extract the shortest expression for each E-class.
        expressions: list[Expression | None] = [None] * (1 + structure.item_count)
        for ob in order:
            # Skip if this object has zero probability
            if best[ob].item() <= 0:
                continue

            # Find the best grammar rule to apply.
            best_prob: float = 0.0
            best_expr: Expression | None = None

            # Nullary functions.
            if ob in nullary_functions:
                prob = self.nullary_functions[ob].item()
                if prob > best_prob:
                    best_prob = prob
                    name = nullary_functions[ob]
                    best_expr = Expression.make(name)

            # Binary functions.
            for self_fs, struct_fs in [
                (self.binary_functions, structure.binary_functions),
                (self.symmetric_functions, structure.symmetric_functions),
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
                    lhs_expr = expressions[lhs_ob]
                    rhs_expr = expressions[rhs_ob]
                    if lhs_expr is None or rhs_expr is None:
                        continue
                    best_prob = value
                    best_expr = Expression.make(name, lhs_expr, rhs_expr)

            expressions[ob] = best_expr

        # Check that all expressions were successfully extracted.
        extracted_count = sum(1 for e in expressions[1:] if e is not None)
        logger.info(f"Extracted {extracted_count}/{structure.item_count} obs")
        expected_count = (best[1:] > 0).long().sum().item()
        assert extracted_count == expected_count

        return expressions

    def count_nonzero_nullary(self) -> int:
        """Count number of nonzero nullary function weights."""
        return (self.nullary_functions.abs() > 1e-8).sum().item()

    def compute_target_sparsity(self, corpus_size: int) -> int:
        """Compute target sparsity as sqrt of corpus size."""
        return int(math.sqrt(corpus_size))

    def compute_l1_penalty(self) -> torch.Tensor:
        """Compute L1 penalty on nullary function weights."""
        return self.nullary_functions.abs().sum()

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

    def fit(
        self,
        structure: Structure,
        corpus: "ObTree | Language",
        *,
        l1_lambda: float = 0.0,
        max_steps: int = 50,
        learning_rate: float = 0.1,
        tol: float = 1e-6,
        reltol: float = 1e-4,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Fit language weights to corpus using gradient descent with L1 regularization.

        Args:
            structure: The E-graph structure
            corpus: Training corpus (ObTree or Language with counts)
            l1_lambda: L1 regularization strength for sparsity control
            max_steps: Maximum optimization steps
            learning_rate: Learning rate for L-BFGS
            tol: Tolerance for optimization convergence
            reltol: Relative tolerance for compute_probs iterations
            verbose: Whether to print progress

        Returns:
            Dictionary with training metrics (loss, sparsity, etc.)
        """
        # Convert corpus to data tensor
        if isinstance(corpus, ObTree):
            # Count occurrences in ObTree
            symbol_counts: Counter[str] = Counter()
            ob_counts: Counter[Ob] = Counter()
            corpus.count(symbol_counts, ob_counts)

            # Convert to data tensor
            data = torch.zeros_like(self.nullary_functions)
            for ob, count in ob_counts.items():
                data[ob] = float(count)
        else:
            # Use corpus language's nullary functions as data
            data = corpus.nullary_functions.detach().clone()

        corpus_size = int(data.sum().item())
        target_sparsity = self.compute_target_sparsity(corpus_size)

        if verbose:
            initial_sparsity = self.count_nonzero_nullary()
            logger.info(
                f"Fitting to corpus of size {corpus_size}, "
                f"target sparsity {target_sparsity}, "
                f"initial sparsity {initial_sparsity}, "
                f"L1 lambda {l1_lambda}"
            )

        # Setup optimizer
        optimizer = torch.optim.LBFGS(
            self.parameters(),
            lr=learning_rate,
            max_iter=20,
            tolerance_grad=tol,
            tolerance_change=tol,
            history_size=10,
        )

        # Track metrics
        losses = []
        sparsities = []
        likelihoods = []
        l1_penalties = []

        # Warm start for compute_probs
        prev_probs = None

        def closure():
            nonlocal prev_probs
            optimizer.zero_grad()

            # Compute probabilities with warm start
            probs = self.compute_probs(
                structure, reltol=reltol, init_probs=prev_probs, min_iterations=3
            )
            prev_probs = probs.detach()

            # Compute log-likelihood term
            tiny = torch.finfo(probs.dtype).tiny
            log_likelihood = torch.xlogy(data, probs + tiny).sum()

            # Compute L1 penalty
            l1_penalty = self.compute_l1_penalty()

            # Total loss (negative log-likelihood + L1 penalty)
            loss = -log_likelihood + l1_lambda * l1_penalty

            # Backward pass
            loss.backward()

            return loss

        # Optimization loop
        for step in range(max_steps):
            # Take optimization step
            loss = optimizer.step(closure)

            # Project to feasible set
            self.project_to_feasible_()

            # Compute metrics
            with torch.no_grad():
                probs = self.compute_probs(
                    structure, reltol=reltol, init_probs=prev_probs
                )
                tiny = torch.finfo(probs.dtype).tiny
                likelihood = torch.xlogy(data, probs + tiny).sum().item()
                l1_penalty = self.compute_l1_penalty().item()
                sparsity = self.count_nonzero_nullary()

                losses.append(loss.item())
                likelihoods.append(likelihood)
                l1_penalties.append(l1_penalty)
                sparsities.append(sparsity)

                if verbose and (step % 10 == 0 or step == max_steps - 1):
                    logger.info(
                        f"Step {step}: loss={loss.item():.6f}, "
                        f"likelihood={likelihood:.6f}, "
                        f"L1={l1_penalty:.6f}, "
                        f"sparsity={sparsity}/{len(self.nullary_functions)}"
                    )

        return {
            "losses": losses,
            "likelihoods": likelihoods,
            "l1_penalties": l1_penalties,
            "sparsities": sparsities,
            "final_sparsity": sparsities[-1],
            "target_sparsity": target_sparsity,
            "corpus_size": corpus_size,
        }
