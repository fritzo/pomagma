import re
import sys
from collections.abc import Callable
from typing import Any

from pomagma.compiler import signature
from pomagma.compiler.signature import ARITY_TABLE
from pomagma.compiler.util import inputs, sortedset, union
from pomagma.util.hashcons import HashConsArgsMeta

re_name = re.compile("[a-zA-Z][a-zA-Z0-9_]*$")
re_space = re.compile("[ _]+")


class Expression(metaclass=HashConsArgsMeta):
    __slots__ = [
        "_name",
        "_args",
        "_arity",
        "_polish",
        "_hash",
        "_sort",
        "_var",
        "_vars",
        "_consts",
        "_terms",
        "__weakref__",
    ]

    def __init__(self, name: str, *args: "Expression") -> None:
        assert isinstance(name, str), type(name)
        assert re_name.match(name), name
        arity = signature.get_arity(name)
        assert len(args) == signature.get_nargs(arity), (args, arity)
        for arg in args:
            assert isinstance(arg, Expression), arg
        self._name = sys.intern(name)
        self._args = args
        self._arity = arity
        self._polish: str = sys.intern(" ".join([name] + [arg._polish for arg in args]))
        self._hash: int = hash(self._polish)
        self._sort: tuple[int, str] = (len(self._polish), self._polish)
        # all other fields are lazily initialized
        self._var: Expression | None = None
        self._vars: set[Expression] | None = None
        self._consts: sortedset[Expression] | None = None
        self._terms: sortedset[Expression] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def args(self) -> tuple["Expression", ...]:
        return self._args

    @property
    def arity(self) -> str:
        return self._arity

    @property
    def polish(self) -> str:
        return self._polish

    @property
    def var(self) -> "Expression | None":
        if self._var is None:
            if self._arity == "Variable":
                self._var = self
            elif self._arity == "NullaryFunction":
                self._var = Expression(self._name + "_")
            elif self._arity in signature.FUNCTION_ARITIES:
                var = re_space.sub("_", self._polish.rstrip("_"))
                self._var = Expression(var)
            # TODO should we handle other cases here?
        return self._var

    @property
    def vars(self) -> set["Expression"]:
        if self._vars is None:
            if self._arity == "Variable":
                result = {self}
            elif self._arity == "NullaryFunction":
                result = set()
            elif self._arity in signature.FUNCTION_ARITIES:
                result = union(a.vars for a in self._args)
            else:
                result = union(a.vars for a in self._args)
            self._vars = sortedset(result)
        return self._vars

    @property
    def consts(self) -> sortedset["Expression"]:
        if self._consts is None:
            if self.is_fun() and not self._args:
                self._consts = sortedset([self])
            else:
                self._consts = sortedset(union(a.consts for a in self._args))
        return self._consts

    @property
    def terms(self) -> sortedset["Expression"]:
        if self._terms is None:
            result = union(a.terms for a in self._args)
            if self.is_term():
                result.add(self)
            self._terms = sortedset(result)
        return self._terms

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: Any) -> bool:
        assert isinstance(other, Expression), other
        return self._polish is other._polish

    def __lt__(self, other: "Expression") -> bool:
        return self._sort < other._sort

    def __str__(self) -> str:
        return self._polish

    def __repr__(self):
        return self._polish

    def is_var(self) -> bool:
        return signature.is_var(self.name)

    def is_fun(self) -> bool:
        return signature.is_fun(self.name)

    def is_rel(self) -> bool:
        return signature.is_rel(self.name)

    def is_meta(self) -> bool:
        return signature.is_meta(self.name)

    def is_term(self) -> bool:
        return signature.is_term(self.name)

    def substitute(self, var: "Expression", defn: "Expression") -> "Expression":
        assert isinstance(var, Expression) and var.is_var()
        assert isinstance(defn, Expression)
        if var not in self.vars:
            return self
        if self.is_var():
            return defn
        return Expression(self.name, *(arg.substitute(var, defn) for arg in self._args))

    def replace(self, pattern: "Expression", replacement: "Expression") -> "Expression":
        """
        Replace all occurrences of pattern with replacement in expression.

        Args:
            pattern: Expression pattern to find and replace
            replacement: Expression to substitute for the pattern

        Returns:
            New expression with pattern replaced by replacement
        """
        assert isinstance(pattern, Expression)
        assert isinstance(replacement, Expression)

        # If this expression matches the pattern exactly, replace it
        if self is pattern:
            return replacement

        # Otherwise, recursively apply to arguments
        new_args = []
        changed = False
        for arg in self._args:
            new_arg = arg.replace(pattern, replacement)
            new_args.append(new_arg)
            if new_arg is not arg:
                changed = True

        # If no changes were made, return self (for efficiency)
        if not changed:
            return self

        # Create new expression with replaced arguments
        result = Expression(self.name, *new_args)

        # Check if the newly created expression matches the pattern
        if result is pattern:
            result = replacement

        return result

    def swap(self, var1: "Expression", var2: "Expression") -> "Expression":
        assert isinstance(var1, Expression) and var1.is_var()
        assert isinstance(var2, Expression) and var2.is_var()
        if var1 not in self.vars and var2 not in self.vars:
            return self
        if self == var1:
            return var2
        if self == var2:
            return var1
        return Expression(self.name, *(arg.swap(var1, var2) for arg in self._args))

    def permute_symbols(self, perm: dict[str, str]) -> "Expression":
        assert isinstance(perm, dict)
        name = "_".join(perm.get(n, n) for n in self.name.split("_"))
        args = (a.permute_symbols(perm) for a in self._args)
        return Expression(name, *args)

    def abstract(self, var: "Expression") -> "Expression":
        raise NotImplementedError("defined in extensional.py")


def Expression_0(name: str) -> "Expression":
    return Expression(name)


def Expression_1(name: str) -> Callable[[Expression], "Expression"]:
    return lambda x: Expression(name, x)


def Expression_2(name: str) -> Callable[[Expression, Expression], "Expression"]:
    return lambda x, y: Expression(name, x, y)


class NotNegatable(Exception):
    pass


def try_negate_name(pos: str) -> str:
    assert pos in ARITY_TABLE
    neg = pos[1:] if pos.startswith("N") else "N" + pos
    if neg not in ARITY_TABLE or ARITY_TABLE[neg] != ARITY_TABLE[pos]:
        raise NotNegatable
    return neg


@inputs(Expression)
def try_get_negated(expr: "Expression") -> set["Expression"]:
    """Returns a disjunction."""
    if expr.name == "EQUAL":
        lhs, rhs = expr.args
        return {Expression("NLESS", lhs, rhs), Expression("NLESS", rhs, lhs)}
    neg_name = try_negate_name(expr.name)
    return {Expression(neg_name, *expr.args)}
