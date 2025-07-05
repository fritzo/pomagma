import itertools

from pomagma.compiler.completion import (
    Inconsistent,
    strengthen_sequent,
    try_simplify_antecedents,
    weaken_sequent,
)
from pomagma.compiler.expressions import Expression, NotNegatable, try_get_negated
from pomagma.compiler.util import inputs, set_with, set_without, union


class Sequent:
    __slots__ = ["_antecedents", "_succedents", "_hash", "_str", "debuginfo"]

    def __init__(self, antecedents, succedents):
        antecedents = frozenset(antecedents)
        succedents = frozenset(succedents)
        for expr in antecedents | succedents:
            assert isinstance(expr, Expression)
        self._antecedents = antecedents
        self._succedents = succedents
        self._hash = hash((antecedents, succedents))
        self._str = None
        self.debuginfo = {}

    @property
    def antecedents(self):
        return self._antecedents

    @property
    def succedents(self):
        return self._succedents

    @property
    def optional(self):
        return all(s.name == "OPTIONALLY" for s in self.succedents)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return (
            self._antecedents == other._antecedents
            and self._succedents == other._succedents
        )

    def __lt__(self, other):
        s = str(self)
        o = str(other)
        return (len(s), s) < (len(o), o)

    def __print_set(self, items, sep=", "):
        items = list(map(str, items))
        items.sort(key=lambda s: (len(s), s))
        return sep.join(items)

    def __str__(self):
        if self._str is None:
            self._str = f"{self.__print_set(self.antecedents)} |- {self.__print_set(self.succedents)}"
        return self._str

    def __repr__(self):
        return f"Sequent({self})"

    def ascii(self, indent=0):
        top = self.__print_set(self.antecedents, sep="   ")
        bot = self.__print_set(self.succedents, sep="   ")
        width = max(len(top), len(bot))
        top = top.center(width)
        bot = bot.center(width)
        bar = "-" * width
        lines = [top, bar, bot]
        lines = list(filter(bool, lines))
        lines = list(map((" " * indent).__add__, lines))
        return "\n".join(lines)

    @property
    def vars(self):
        return union(s.vars for s in self.antecedents | self.succedents)

    @property
    def consts(self):
        return union(s.consts for s in self.antecedents | self.succedents)

    def permute_symbols(self, perm):
        assert isinstance(perm, dict)
        return Sequent(
            (e.permute_symbols(perm) for e in self.antecedents),
            (e.permute_symbols(perm) for e in self.succedents),
        )


@inputs(Expression)
def as_atom(expr):
    args = [arg.var for arg in expr.args]
    return Expression(expr.name, *args)


@inputs(Expression)
def as_antecedents(expr, bound):
    antecedents = set()
    while expr.name in ["OPTIONALLY", "NONEGATE"]:
        expr = expr.args[0]
    if expr.arity != "Variable":
        atom = as_atom(expr)
        if not (atom.var in bound and all(arg in bound for arg in atom.args)):
            antecedents.add(atom)
        for arg in expr.args:
            antecedents |= as_antecedents(arg, bound)
    return antecedents


@inputs(Expression)
def as_succedent(expr, bound):
    while expr.name in ["OPTIONALLY", "NONEGATE"]:
        expr = expr.args[0]
    antecedents = set()
    if expr.arity == "Equation":
        args = []
        for arg in expr.args:
            if arg.is_var() or arg.var in bound:
                args.append(arg.var)
            elif arg.args:
                args.append(as_atom(arg))
                for argarg in arg.args:
                    antecedents |= as_antecedents(argarg, bound)
            else:
                assert arg.arity == "NullaryFunction", arg
                args.append(arg.var)
                antecedents.add(arg)
        succedent = Expression(expr.name, *args)
    else:
        assert expr.args, expr.args
        succedent = as_atom(expr)
        for arg in expr.args:
            antecedents |= as_antecedents(arg, bound)
    return antecedents, succedent


@inputs(Sequent)
def get_pointed(seq):
    """Return a set of sequents each with a single succedent."""
    result = set()
    if len(seq.succedents) == 1:
        for succedent in seq.succedents:
            if succedent.name != "OPTIONALLY":
                result.add(seq)
    elif len(seq.succedents) > 1:
        for succedent in seq.succedents:
            remaining = set_without(seq.succedents, succedent)
            try:
                neg_remaining = list(map(try_get_negated, remaining))
            except NotNegatable:
                continue
            for negated in itertools.product(*neg_remaining):
                try:
                    antecedents = try_simplify_antecedents(
                        set(negated) | seq.antecedents
                    )
                except Inconsistent:
                    continue
                result.add(Sequent(antecedents, {succedent}))
    else:
        raise ValueError("get_contrapositives never returns empty succedents")
    return result


@inputs(Sequent)
def get_atomic(seq, bound=set()):
    """Return a set of normal sequents.

    Atoms whose every variable is bound are excluded from antecedents.

    """
    result = set()
    for pointed in get_pointed(seq):
        improper_succedent = next(iter(pointed.succedents))
        improper_succedent = strengthen_sequent(improper_succedent)
        antecedents, succedent = as_succedent(improper_succedent, bound)
        for a in pointed.antecedents:
            antecedents |= as_antecedents(a, bound)
        result.add(Sequent(antecedents, {succedent}))
    return result


@inputs(Sequent)
def get_contrapositives(seq):
    """Given multiple antecedents and succedents, return a set of sequents with
    various antecedents or succedents negated such that each result sequent
    corresponds has a succedent set corresponding to exactly one of the
    original antecedents or succedents. For example.

        A, B |- C, D

    yields the set

        B, ~C, ~D |- ~A
        A, ~C, ~D |- ~B
        A, B, ~D |- C
        A, B, ~C |- D

    """
    ante_succ_pairs = []
    for succedent in map(weaken_sequent, seq.succedents):
        try:
            antecedents = try_get_negated(succedent)
        except NotNegatable:
            antecedents = set()
        ante_succ_pairs.append((antecedents, {succedent}))
    for antecedent in map(weaken_sequent, seq.antecedents):
        try:
            succedents = try_get_negated(antecedent)
        except NotNegatable:
            succedents = set()
        ante_succ_pairs.append(({antecedent}, succedents))
    result = set()
    for _, succedents in ante_succ_pairs:
        if succedents:
            succedent = next(iter(succedents))
            antecedents_product = []
            for other_antecedents, other_succedents in ante_succ_pairs:
                if other_succedents != succedents:
                    antecedents_product.append(other_antecedents)
            for antecedents in itertools.product(*antecedents_product):
                if succedent in antecedents:
                    continue
                try:
                    antecedents = try_simplify_antecedents(set(antecedents))
                except Inconsistent:
                    continue
                result.add(Sequent(antecedents, succedents))
    return result


@inputs(Sequent)
def get_inverses(sequent):
    """
    Given a sequent A |- B, return set of sequents ~A |- ~B,
    dealing with multiple antecedents and succedents. For example

        A, B |- C, D

    yields the set

        A, ~B |- ~C, ~D
        ~A, B |- ~C, ~D
    """
    result = set()
    neg_succedents = union(try_get_negated(s) for s in sequent.succedents)
    pos_antecedents = set(sequent.antecedents)
    for pos_antecedent in pos_antecedents:
        try:
            negated = try_get_negated(pos_antecedent)
        except NotNegatable:
            negated = set()
        for neg_antecedent in negated:
            neg_antecedents = set_without(pos_antecedents, pos_antecedent)
            neg_antecedents = set_with(neg_antecedents, neg_antecedent)
            result.add(Sequent(neg_antecedents, neg_succedents))
    return result


@inputs(Sequent)
def normalize(seq, bound=set()):
    """Return a set of normal sequents, closed under contrapositive.

    Atoms whose every variable is bound are excluded from antecedents.

    """
    if seq.optional:
        return set()
    result = set()
    for contra in get_contrapositives(seq):
        result |= get_atomic(contra, bound)
    assert result, f"failed to normalize {seq} binding {bound}"
    return result


@inputs(Sequent)
def assert_normal(seq):
    assert len(seq.succedents) == 1
    for expr in seq.antecedents:
        for arg in expr.args:
            assert arg.arity == "Variable", arg
    for expr in seq.succedents:
        if expr.arity == "Equation":
            for arg in expr.args:
                for arg_arg in arg.args:
                    assert arg_arg.arity == "Variable", arg_arg
        else:
            for arg in expr.args:
                assert arg.arity == "Variable", arg
