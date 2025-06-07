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
        """
        Count occurrences of symbols and E-classes in this expression tree.

        This method traverses the ObTree and extracts two types of counts:

        Args:
            symbol_counts: Counter to accumulate function symbol usage counts.
                For each internal node with a function name (e.g., "APP", "COMP"),
                increments the count for that symbol.
            ob_counts: Counter to accumulate E-class occurrence counts.
                For each leaf node that is fully reduced to an E-class (Ob),
                increments the count for that E-class.

        Example:
            For the expression APP(X, Y) where X and Y are E-classes:
            - symbol_counts["APP"] += 1  (the APP function is used once)
            - ob_counts[X] += 1          (E-class X appears once)
            - ob_counts[Y] += 1          (E-class Y appears once)

        This separation is crucial for fitting Language models, where:
        - ob_counts determine the target distribution over E-classes
        - symbol_counts determine the target weights for function symbols
        """
        if self.ob:
            ob_counts[self.ob] += 1
        else:
            assert self.name is not None
            assert self.args is not None
            symbol_counts[self.name] += 1
            for arg in self.args:
                arg.count(symbol_counts, ob_counts)
