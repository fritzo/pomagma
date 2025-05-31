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

    def propagate_probs(
        self, structure: Structure, *, tol: float = 1e-6
    ) -> torch.Tensor:
        assert 0.0 < tol < 1.0
        # Initialize with atoms.
        probs = self.nullary_functions / self.nullary_functions.sum()

        # Propagate until convergence.
        diff = 1.0
        while diff > tol:
            prev = probs
            probs = self._propagate_probs_step(structure, probs)
            with torch.no_grad():
                diff = (probs - prev).abs().sum().item()

        return probs

    def _propagate_probs_step(
        self, structure: Structure, probs: torch.Tensor
    ) -> torch.Tensor:
        out = self.nullary_functions.clone()
        for name, weight in self.binary_functions.items():
            fn = structure.binary_functions[name]
            out += weight * fn.sum_product(probs, probs)
        for name, weight in self.symmetric_functions.items():
            fn = structure.symmetric_functions[name]
            out += weight * fn.sum_product(probs, probs)
        return out

    def log_prob(self, data: "Language") -> torch.Tensor:
        """
        Compute the log probability of data under this probabilistic language.
        """
        h = torch.nn.functional.cross_entropy(
            data.nullary_functions, self.nullary_functions, reduction="sum"
        )
        weights: list[torch.Tensor] = []
        probs: list[torch.Tensor] = []
        for name, weight in data.injective_functions.items():
            probs.append(self.injective_functions[name])
            weights.append(weight)
        for name, weight in data.binary_functions.items():
            probs.append(self.binary_functions[name])
            weights.append(weight)
        for name, weight in data.symmetric_functions.items():
            probs.append(self.symmetric_functions[name])
            weights.append(weight)
        if weights:
            h += torch.nn.functional.cross_entropy(
                torch.stack(weights), torch.stack(probs), reduction="sum"
            )
        return -h

    def iadd_corpus(self, ob_tree: ObTree, weight: float = 1.0) -> None:
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
