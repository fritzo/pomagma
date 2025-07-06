import logging
from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass
from typing import TYPE_CHECKING

import torch
from immutables import Map

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.util import memoize_weak_strong, weak_memoize_1, weak_memoize_2
from pomagma.reducer.curry import convert
from pomagma.util.hashcons import WeakHashConsMeta

from .structure import Ob, Structure

if TYPE_CHECKING:
    from pomagma.reducer.syntax import Term

logger = logging.getLogger(__name__)

EMPTY_OB_MAP: Map[Ob, int] = Map()
EMPTY_STR_MAP: Map[str, int] = Map()


@dataclass(frozen=True, slots=True)
class CorpusStats:
    """Counts of symbols and E-classes in a corpus."""

    obs: Map[Ob, int] = EMPTY_OB_MAP
    symbols: Map[str, int] = EMPTY_STR_MAP

    def __add__(self, other: "CorpusStats") -> "CorpusStats":
        obs = Counter(self.obs)
        obs.update(other.obs)
        symbols = Counter(self.symbols)
        symbols.update(other.symbols)
        return CorpusStats(obs=Map(obs), symbols=Map(symbols))


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ObTree(metaclass=WeakHashConsMeta):
    """A partially understood expression, whose leaves are Obs i.e. E-classes."""

    ob: Ob | None = None
    name: str | None = None
    args: tuple["ObTree", ...] | frozenset["ObTree"] | None = None

    @staticmethod
    @weak_memoize_2
    def from_expr(
        structure: Structure,
        expr: Expression,
        *,
        strict: bool = True,
    ) -> "ObTree":
        """Create an ObTree from a pomagma.compiler.expressions.Expression."""
        name = expr.name
        args: tuple[ObTree, ...] = tuple(
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
                return ObTree(name=name, args=args)
        elif expr.arity == "SymmetricFunction":
            if name in structure.symmetric_functions:
                fn = structure.symmetric_functions[name]
                assert args[0].ob
                assert args[1].ob
                if ob := fn[args[0].ob, args[1].ob]:
                    return ObTree(ob=ob)
                return ObTree(name=name, args=frozenset(args))
        if strict:
            raise ValueError(f"Unknown symbol: {name}")
        logger.warning("Unknown symbol: %s", name)
        return ObTree(name=name, args=args)

    @staticmethod
    def from_term(
        structure: Structure, term: "Term", *, strict: bool = True
    ) -> "ObTree":
        """Create an ObTree from a pomagma.reducer.syntax.Term."""
        term = convert(term)  # eliminate abstraction
        return ObTree._from_term(structure, term, strict=strict)

    @staticmethod
    @memoize_weak_strong
    def _from_term(
        structure: Structure, term: "Term", *, strict: bool = True
    ) -> "ObTree":
        name: str = term[0]
        if name in ("ABS", "FUN", "NVAR", "IVAR"):
            raise NotImplementedError(f"Variables are not allowed: {name}")
        args: tuple[ObTree, ...] = tuple(
            ObTree._from_term(structure, arg, strict=strict) for arg in term[1:]
        )
        if not all(arg.ob for arg in args):
            return ObTree(name=name, args=args)
        if len(args) == 0:
            if nullary := structure.nullary_functions.get(name):
                return ObTree(ob=nullary)
        elif len(args) == 2:
            lhs: Ob = args[0].ob  # type: ignore[assignment]
            rhs: Ob = args[1].ob  # type: ignore[assignment]
            if binary := structure.binary_functions.get(name):
                if ob := binary[lhs, rhs]:
                    return ObTree(ob=ob)
            elif symmetric := structure.symmetric_functions.get(name):
                if ob := symmetric[lhs, rhs]:
                    return ObTree(ob=ob)
        if strict:
            raise ValueError(f"Unknown symbol: {name}")
        logger.warning("Unknown symbol: %s", name)
        return ObTree(name=name, args=args)

    @staticmethod
    def from_string(
        structure: Structure,
        string: str,
        *,
        strict: bool = False,
    ) -> "ObTree":
        """Create an ObTree from a string in polish notation."""
        expr = parse_string_to_expr(string)
        return ObTree.from_expr(structure, expr, strict=strict)

    def __str__(self) -> str:
        if self.ob:
            return f"[{self.ob}]"
        assert self.name is not None
        assert self.args is not None
        parts = [self.name, *map(str, self.args)]
        return " ".join(parts)

    @staticmethod
    def from_join(structure: Structure, args: Collection["ObTree"]) -> "ObTree":
        """Construct a finitary join from a collection of ObTrees."""
        if len(args) == 0:
            return ObTree(ob=structure.nullary_functions["BOT"])
        if len(args) == 1:
            return next(iter(args))
        return ObTree(name="JOIN", args=frozenset(args))

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
            if isinstance(self.args, tuple):
                symbols[self.name] += 1
            elif isinstance(self.args, frozenset):  # finitary joins
                symbols[self.name] += len(self.args) - 1
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
