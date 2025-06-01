from collections import Counter
from typing import Mapping

import torch
from immutables import Map

from .corpus import ObTree
from .structure import Ob, Structure

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
        self, structure: Structure, *, reltol: float = 1e-3
    ) -> torch.Tensor:
        """
        Propagates from a normalized grammar to a sub-normalized weighted set of obs.

        (The ob set would be normalized if the structure were closed, but the
        structure is only a finite subset of the full structure.)
        """
        assert 0.0 < reltol < 1.0
        eps = torch.finfo(self.nullary_functions.dtype).eps

        # Initialize with atoms.
        probs = self.nullary_functions / self.nullary_functions.sum()

        # Propagate until convergence.
        diff = 1.0
        while diff > reltol:
            prev = probs
            probs = self._compute_probs_step(structure, probs)
            with torch.no_grad():
                # Only the convergence check is in no_grad - doesn't affect gradients
                diffs = (probs - prev).abs() / (probs + eps)
                diff = diffs.max().item()

        return probs

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

    def compute_occurrences(
        self, structure: Structure, data: torch.Tensor, *, reltol=1e-3
    ) -> torch.Tensor:
        """
        Counts the effective number of occurrences of each ob in the data, averaged
        over extractions.
        """
        # This uses Eisner's gradient trick: the gradient of log P(data | probs)
        # with respect to grammar parameters gives the expected count of each
        # grammar rule/E-class.
        assert data.shape == self.nullary_functions.shape
        assert 0.0 < reltol < 1.0

        # Compute the "inside" probabilities with gradient tracking
        self.nullary_functions.requires_grad_(True)
        probs = self.compute_probs(structure, reltol=reltol)

        # Compute log-probability of observed data under the probability distribution
        # log P(data | probs) = ∑_i data[i] * log(probs[i])
        tiny = torch.finfo(probs.dtype).tiny
        log_likelihood = torch.xlogy(data, probs + tiny).sum()

        # Apply Eisner's gradient trick: ∂/∂params log P(data | params) = E[counts]
        # The gradient automatically propagates through the E-graph structure
        grad_nullary = torch.autograd.grad(
            outputs=log_likelihood,
            inputs=self.nullary_functions,
            create_graph=False,
            retain_graph=False,
            only_inputs=True,
        )[0]

        return grad_nullary

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
