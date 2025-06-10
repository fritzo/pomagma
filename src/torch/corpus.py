import logging
from collections import Counter
from dataclasses import dataclass
from weakref import WeakKeyDictionary

import torch
from immutables import Map

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.util.hashcons import HashConsMeta

from .structure import BinaryFunction, Ob, Structure

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


_STATS: WeakKeyDictionary["ObTree", CorpusStats] = WeakKeyDictionary()


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ObTree(metaclass=HashConsMeta):
    """A partially understood expression, whose leaves are Obs i.e. E-classes."""

    ob: Ob | None = None
    name: str | None = None
    args: tuple["ObTree", ...] | None = None

    @staticmethod
    def from_expr(structure: Structure, expr: Expression) -> "ObTree":
        name = expr.name
        args: tuple["ObTree", ...] = tuple(
            ObTree.from_expr(structure, arg) for arg in expr.args
        )
        if not all(arg.ob for arg in args):
            return ObTree(name=name, args=args)
        if expr.arity == 0:
            if name in structure.nullary_functions:
                return ObTree(ob=structure.nullary_functions[name])
        if expr.arity == 2:
            fn: BinaryFunction | None = None
            if name in structure.binary_functions:
                fn = structure.binary_functions[name]
            elif name in structure.symmetric_functions:
                fn = structure.symmetric_functions[name]
            if fn is not None:
                assert args[0].ob
                assert args[1].ob
                if ob := fn[args[0].ob, args[1].ob]:
                    return ObTree(ob=ob)
        logger.warning(f"Unknown symbol: {name}")
        return ObTree(name=name, args=args)

    @staticmethod
    def from_string(structure: Structure, string: str) -> "ObTree":
        expr = parse_string_to_expr(string)
        return ObTree.from_expr(structure, expr)

    def __str__(self) -> str:
        if self.ob:
            return f"[{self.ob}]"
        assert self.name is not None
        assert self.args is not None
        parts = [self.name, *map(str, self.args)]
        return " ".join(parts)

    @property
    def stats(self) -> CorpusStats:
        """Count occurrences of symbols and E-classes in this expression dag."""
        # Check cache
        stats = _STATS.get(self, None)
        if stats is not None:
            return stats

        # Count
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

        # Store in cache
        stats = CorpusStats(obs=Map(obs), symbols=Map(symbols))
        _STATS[self] = stats
        return stats

    def materialize(self, structure: Structure) -> torch.Tensor:
        """Convert ObTree stats to dense tensor for compute_occurrences."""
        result = torch.zeros(structure.item_count + 1, dtype=torch.float32)
        for ob, count in self.stats.obs.items():
            result[ob] = count
        return result
