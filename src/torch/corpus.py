import logging
from collections import Counter
from dataclasses import dataclass

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.util.hashcons import HashConsMeta

from .structure import BinaryFunction, Ob, Structure

logger = logging.getLogger(__name__)


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

    # TODO make this O(dag size) rather than O(tree size)
    def count(
        self,
        symbol_counts: Counter[str],
        ob_counts: Counter[Ob],
    ) -> None:
        if self.ob:
            ob_counts[self.ob] += 1
        else:
            assert self.name is not None
            assert self.args is not None
            symbol_counts[self.name] += 1
            for arg in self.args:
                arg.count(symbol_counts, ob_counts)
