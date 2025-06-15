import logging
from collections import Counter
from dataclasses import dataclass

import torch
from immutables import Map

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.util import weak_memoize_1, weak_memoize_2
from pomagma.util.hashcons import HashConsMeta

from .structure import Ob, Structure

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CorpusStats:
    """Counts of symbols and E-classes in a corpus."""

    obs: Map[Ob, int] = Map()
    symbols: Map[str, int] = Map()

    def __add__(self, other: "CorpusStats") -> "CorpusStats":
        obs = Counter(self.obs)
        obs.update(other.obs)
        symbols = Counter(self.symbols)
        symbols.update(other.symbols)
        return CorpusStats(obs=Map(obs), symbols=Map(symbols))


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ObTree(metaclass=HashConsMeta):
    """A partially understood expression, whose leaves are Obs i.e. E-classes."""

    ob: Ob | None = None
    name: str | None = None
    args: tuple["ObTree", ...] | None = None

    @staticmethod
    @weak_memoize_2
    def from_expr(
        structure: Structure,
        expr: Expression,
        *,
        strict: bool = True,
    ) -> "ObTree":
        name = expr.name
        args: tuple["ObTree", ...] = tuple(
            ObTree.from_expr(structure, arg, strict=strict) for arg in expr.args
        )
        if not all(arg.ob for arg in args):
            return ObTree(name=name, args=args)
        if expr.arity == "NullaryFunction":
            if name in structure.nullary_functions:
                return ObTree(ob=structure.nullary_functions[name])
        elif expr.arity == "BinaryFunction":
            if name in structure.binary_functions:
                fn = structure.binary_functions[name]
                assert args[0].ob
                assert args[1].ob
                if ob := fn[args[0].ob, args[1].ob]:
                    return ObTree(ob=ob)
                else:
                    return ObTree(name=name, args=args)
        elif expr.arity == "SymmetricFunction":
            if name in structure.symmetric_functions:
                fn = structure.symmetric_functions[name]
                assert args[0].ob
                assert args[1].ob
                if ob := fn[args[0].ob, args[1].ob]:
                    return ObTree(ob=ob)
                else:
                    return ObTree(name=name, args=args)
        if strict:
            raise ValueError(f"Unknown symbol: {name}")
        logger.warning(f"Unknown symbol: {name}")
        return ObTree(name=name, args=args)

    @staticmethod
    def from_string(
        structure: Structure,
        string: str,
        *,
        strict: bool = False,
    ) -> "ObTree":
        expr = parse_string_to_expr(string)
        return ObTree.from_expr(structure, expr, strict=strict)

    def __str__(self) -> str:
        if self.ob:
            return f"[{self.ob}]"
        assert self.name is not None
        assert self.args is not None
        parts = [self.name, *map(str, self.args)]
        return " ".join(parts)

    @property
    @weak_memoize_1
    def stats(self) -> CorpusStats:
        """Count occurrences of symbols and E-classes in this expression dag."""
        obs: Counter[Ob] = Counter()
        symbols: Counter[str] = Counter()
        if self.ob:
            obs[self.ob] += 1
        else:
            assert self.name is not None
            assert self.args is not None
            symbols[self.name] += 1
            for arg in self.args:
                stats = arg.stats
                obs.update(stats.obs)
                symbols.update(stats.symbols)
        return CorpusStats(obs=Map(obs), symbols=Map(symbols))

    def materialize(self, structure: Structure) -> torch.Tensor:
        """Convert ObTree stats to dense tensor for compute_occurrences."""
        result = torch.zeros(structure.item_count + 1, dtype=torch.float32)
        for ob, count in self.stats.obs.items():
            result[ob] = count
        return result
