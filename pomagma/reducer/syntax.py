"""Lightweight immutable terms."""

import re
import sys
from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import Any, ClassVar, ParamSpec, TypeAlias

from pomagma.compiler.util import memoize_arg, memoize_args, unique_result
from pomagma.reducer.util import UnreachableError

_A = ParamSpec("_A")

Sexpr: TypeAlias = str | int | tuple["Sexpr", ...]

################################################################
# Signature


class Term(tuple[str, *tuple["Term | str | int", ...]]):
    """A term is a tuple of a keyword and a list of arguments."""

    __slots__ = ()

    def __repr__(self) -> str:
        if len(self) == 1:
            return self[0]
        return "{}({})".format(self[0], ", ".join(repr(a) for a in self[1:]))

    def __str__(self) -> str:
        if len(self) == 1:
            return self[0]
        return "{}({})".format(self[0], ", ".join(str(a) for a in self[1:]))

    def __call__(*args: Any) -> "Term":
        # This syntax will be defined later:
        # return pomagma.reducer.sugar.app(*args)
        raise NotImplementedError("import pomagma.reduce.sugar")

    def __or__(self: "Term", rhs: "Term") -> "Term":
        # This syntax will be defined later:
        # return pomagma.reducer.sugar.join_(lhs, rhs)
        raise NotImplementedError("import pomagma.reduce.sugar")

    @staticmethod
    @memoize_args
    def make(*args: "Term | str | int") -> "Term":
        return Term(args)


re_keyword = re.compile("[A-Z]+$")
re_rank = re.compile(r"\d+$")
_keywords = {}  # : name -> arity
_builders = {}  # : name -> constructor
_atoms = {}  # name -> term


def make_keyword(name: str, arity: int) -> str:
    assert re_keyword.match(name)
    assert name not in _keywords
    assert arity in [0, 1, 2]
    name = sys.intern(name)
    _keywords[name] = arity
    return name


def make_atom(name: str) -> Term:
    assert name not in _atoms
    name = make_keyword(name, arity=0)
    term = Term.make(name)
    _atoms[name] = term
    return term


def builder(fun: Callable[_A, Term]) -> Callable[_A, Term]:
    name = sys.intern(fun.__name__)
    assert name in _keywords, name
    assert _keywords[name] > 0, (name, _keywords[name])
    assert name not in _builders, name
    _builders[name] = fun
    return fun


_IVAR = make_keyword("IVAR", 1)  # de Bruijn variable.
_NVAR = make_keyword("NVAR", 1)  # Nominal variable.
_APP = make_keyword("APP", 2)
_JOIN = make_keyword("JOIN", 2)
_RAND = make_keyword("RAND", 2)
_QUOTE = make_keyword("QUOTE", 1)
_ABS = make_keyword("ABS", 1)  # de Bruijn abstraction.
_FUN = make_keyword("FUN", 2)  # Nominal abstraction.
_LESS = make_keyword("LESS", 2)
_NLESS = make_keyword("NLESS", 2)
_EQUAL = make_keyword("EQUAL", 2)

TOP = make_atom("TOP")
BOT = make_atom("BOT")
I = make_atom("I")
K = make_atom("K")
B = make_atom("B")
C = make_atom("C")
S = make_atom("S")
Y = make_atom("Y")

CODE = make_atom("CODE")
EVAL = make_atom("EVAL")
QAPP = make_atom("QAPP")
QQUOTE = make_atom("QQUOTE")
QEQUAL = make_atom("QEQUAL")
QLESS = make_atom("QLESS")

V = make_atom("V")
A = make_atom("A")
SEMI = make_atom("SEMI")
UNIT = make_atom("UNIT")
BOOL = make_atom("BOOL")
MAYBE = make_atom("MAYBE")
PROD = make_atom("PROD")
SUM = make_atom("SUM")
NUM = make_atom("NUM")


@builder
def NVAR(name: str) -> Term:
    if re_keyword.match(name):
        raise ValueError(f"Variable names cannot match [A-Z]+: {name}")
    return Term.make(_NVAR, sys.intern(name))


@builder
def IVAR(rank: int) -> Term:
    if not (isinstance(rank, int) and rank >= 0):
        raise ValueError(f"Variable index must be a natural number {rank}")
    return Term.make(_IVAR, rank)


IVAR_0 = IVAR(0)


@builder
def APP(lhs: Term, rhs: Term) -> Term:
    return Term.make(_APP, lhs, rhs)


@builder
def JOIN(lhs: Term, rhs: Term) -> Term:
    return Term.make(_JOIN, lhs, rhs)


@builder
def RAND(lhs: Term, rhs: Term) -> Term:
    return Term.make(_RAND, lhs, rhs)


@builder
def QUOTE(term: Term) -> Term:
    # TODO assert all(not is_ivar(v) for v in free_vars(term))
    return Term.make(_QUOTE, term)


@builder
def ABS(body: Term) -> Term:
    assert IVAR_0 not in quoted_vars(body)
    return Term.make(_ABS, body)


@builder
def FUN(var: Term, body: Term) -> Term:
    assert is_nvar(var), var
    assert var not in quoted_vars(body), (var, body)
    return Term.make(_FUN, var, body)


@builder
def LESS(lhs: Term, rhs: Term) -> Term:
    return Term.make(_LESS, lhs, rhs)


@builder
def NLESS(lhs: Term, rhs: Term) -> Term:
    return Term.make(_NLESS, lhs, rhs)


@builder
def EQUAL(lhs: Term, rhs: Term) -> Term:
    return Term.make(_EQUAL, lhs, rhs)


def is_atom(term: Term) -> bool:
    assert isinstance(term, Term), term
    return len(term) == 1


def is_nvar(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _NVAR


def is_ivar(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _IVAR


def is_app(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _APP


def is_join(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _JOIN


def is_rand(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _RAND


def is_quote(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _QUOTE


def is_abs(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _ABS


def is_fun(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _FUN


def is_equal(term: Term) -> bool:
    assert isinstance(term, Term), term
    return term[0] is _EQUAL


################################################################
# Transforms


class Transform:
    """Recursive transform of term."""

    # Explicitly declare all dynamically added atom attributes
    TOP: ClassVar[Term]
    BOT: ClassVar[Term]
    I: ClassVar[Term]
    K: ClassVar[Term]
    B: ClassVar[Term]
    C: ClassVar[Term]
    S: ClassVar[Term]
    Y: ClassVar[Term]
    CODE: ClassVar[Term]
    EVAL: ClassVar[Term]
    QAPP: ClassVar[Term]
    QQUOTE: ClassVar[Term]
    QEQUAL: ClassVar[Term]
    QLESS: ClassVar[Term]
    V: ClassVar[Term]
    A: ClassVar[Term]
    SEMI: ClassVar[Term]
    UNIT: ClassVar[Term]
    BOOL: ClassVar[Term]
    MAYBE: ClassVar[Term]
    PROD: ClassVar[Term]
    SUM: ClassVar[Term]
    NUM: ClassVar[Term]

    # Explicitly declare all dynamically added builder methods
    # Note: These are set as staticmethod(builder) by init_class()
    NVAR: Callable[[str], Term]
    IVAR: Callable[[int], Term]
    APP: Callable[[Any, Any], Term]
    JOIN: Callable[[Any, Any], Term]
    RAND: Callable[[Any, Any], Term]
    QUOTE: Callable[[Any], Term]
    ABS: Callable[[Any], Term]
    FUN: Callable[[Any, Any], Term]
    LESS: Callable[[Any, Any], Term]
    NLESS: Callable[[Any, Any], Term]
    EQUAL: Callable[[Any, Any], Term]

    def __init__(self, **kwargs) -> None:
        for key, val in list(kwargs.items()):
            setattr(self, key, val)

    @memoize_args
    def __call__(self, term: Term) -> Term:
        if not isinstance(term, Term):
            raise TypeError(term)
        if is_atom(term):
            return getattr(self, term[0])  # type: ignore[no-any-return]
        if is_nvar(term):
            return self.NVAR(term[1])  # type: ignore[no-any-return]
        if is_ivar(term):
            return self.IVAR(term[1])  # type: ignore[no-any-return]
        args = [self(arg) for arg in term[1:]]  # type: ignore[arg-type]
        return getattr(self, term[0])(*args)  # type: ignore[no-any-return]

    @classmethod
    def init_class(cls):
        for name, term in list(_atoms.items()):
            setattr(cls, name, term)
        for name, builder in list(_builders.items()):
            setattr(cls, name, staticmethod(builder))


Transform.init_class()
identity = Transform()


################################################################
# Variables


def anonymize(term, var, transform=identity):
    """Convert a nominal variable to a de Bruijn variable."""
    return _anonymize(term, var, 0, transform)


@memoize_args
def _anonymize(term, var, rank, transform):
    """Convert a nominal variable to a de Bruijn variable."""
    if term is var:
        return transform.IVAR(rank)
    if is_atom(term) or is_nvar(term):
        return transform(term)
    if is_ivar(term):
        if term[1] < rank:
            return transform.IVAR(term[1])
        return transform.IVAR(term[1] + 1)
    if is_abs(term):
        body = _anonymize(term[1], var, rank + 1, transform)
        return transform.ABS(body)
    if is_app(term):
        lhs = _anonymize(term[1], var, rank, transform)
        rhs = _anonymize(term[2], var, rank, transform)
        return transform.APP(lhs, rhs)
    if is_join(term):
        lhs = _anonymize(term[1], var, rank, transform)
        rhs = _anonymize(term[2], var, rank, transform)
        return transform.JOIN(lhs, rhs)
    if is_rand(term):
        lhs = _anonymize(term[1], var, rank, transform)
        rhs = _anonymize(term[2], var, rank, transform)
        return transform.RAND(lhs, rhs)
    if is_quote(term):
        body = _anonymize(term[1], var, rank, transform)
        return transform.QUOTE(body)
    raise ValueError(term)
    raise UnreachableError(term)


def decrement_var(var):
    """Decrement rank of an IVAR or leave an NVAR untouched."""
    if is_nvar(var):
        return var
    if is_ivar(var):
        assert var[1] > 0, var
        return IVAR(var[1] - 1)
    raise ValueError(var)
    raise UnreachableError(var)


@memoize_arg
@unique_result
def free_vars(term) -> frozenset[Term]:
    """Returns set of free variables, possibly quoted."""
    assert isinstance(term, Term), term
    if is_atom(term):
        return frozenset()
    if is_nvar(term) or is_ivar(term):
        return frozenset([term])
    if is_app(term) or is_join(term) or is_rand(term):
        return free_vars(term[1]) | free_vars(term[2])
    if is_quote(term):
        return free_vars(term[1])
    if is_abs(term):
        return frozenset(
            decrement_var(v) for v in free_vars(term[1]) if v is not IVAR_0
        )
    if is_fun(term):
        v: Term = term[1]  # type: ignore[assignment]
        assert is_nvar(v)
        return free_vars(term[2]) - frozenset([v])
    raise ValueError(term)
    raise UnreachableError(term)


@memoize_arg
@unique_result
def quoted_vars(term):
    """Returns set of free quoted variables."""
    assert isinstance(term, Term), term
    if is_atom(term) or is_nvar(term) or is_ivar(term):
        return frozenset()
    if is_quote(term):
        return free_vars(term[1])
    if is_app(term) or is_join(term) or is_rand(term):
        return quoted_vars(term[1]) | quoted_vars(term[2])
    if is_abs(term):
        return frozenset(
            decrement_var(v) for v in quoted_vars(term[1]) if v is not IVAR_0
        )
    if is_fun(term):
        return quoted_vars(term[2])
    raise ValueError(term)
    raise UnreachableError(term)


@memoize_arg
def is_closed(term):
    """A term is closed if all de Bruijn variables are bound."""
    return not any(is_ivar(v) for v in free_vars(term))


@memoize_arg
def is_defined(term):
    """A term is defined if all nominal variables have been substituted."""
    return not any(is_nvar(v) for v in free_vars(term))


################################################################
# Complexity

# Term complexity is roughly the depth of a term, with special cases for atoms,
# variables, and joins. The complexity of a join is the max complexity of each
# part of the join.
ATOM_COMPLEXITY = defaultdict(
    lambda: 10,
    {
        BOT: 0,
        TOP: 0,
        I: 2,  # \x.x
        K: 3,  # \x,y. x
        B: 6,  # \x,y,z. x (y z)
        C: 6,  # \x,y,z. x z y
        S: 6,  # \x,y,z. x z (y z)
        Y: 6,  # \f. (\x. f(x x)) (\x. f(x x))
        # V: TODO(),
        # A: TODO(),
    },
)


@memoize_arg
def complexity(term):
    """Complexity norm on term.

    Theorem: Modulo alpha conversion and excluding JOIN-terms,
      there are finitely many terms with any fixed complexity.
    Theorem: There are finitely many JOIN-free closed de Bruijn terms
      at any given complexity.

    """
    assert isinstance(term, Term), term
    if is_atom(term):
        return ATOM_COMPLEXITY[term]
    if is_nvar(term) or is_ivar(term):
        return 1
    if is_join(term):
        return max(complexity(term[1]), complexity(term[2]))
    if isinstance(term, tuple):
        return 1 + max(complexity(arg) for arg in term[1:])
    raise ValueError(term)
    raise UnreachableError(term)


################################################################
# Polish notation


def polish_parse(string: str, transform: Transform = identity) -> Term:
    """
    Parse a string from polish notation to a term.

    Args:
      string: a string in polish notation.
      transform: an optional Transform, mapping keyword to builder.

    Returns:
      a python term.

    Example:
      >>> polish_parse('JOIN VAR x JOIN C VAR y')
      ('JOIN', ('VAR', 'x'), ('JOIN', 'C', ('VAR', 'y')))
    """
    assert isinstance(string, str), type(string)
    assert isinstance(transform, Transform), type(transform)
    tokens = list(map(sys.intern, string.split()))
    tokens.reverse()
    return _polish_parse_tokens(tokens, transform)


def _pop_token(tokens, transform):
    return tokens.pop()


def _pop_int(tokens, transform):
    return int(tokens.pop())


def _polish_parse_tokens(tokens: list[str], transform: Transform) -> Term:
    token = tokens.pop()
    try:
        polish_parsers = _PARSERS[token]
    except KeyError:
        if re_keyword.match(token):
            return getattr(transform, token)  # type: ignore[no-any-return]
        if re_rank.match(token):
            return IVAR(int(token))
        return NVAR(token)
    args = tuple(p(tokens, transform) for p in polish_parsers)
    try:
        fun = getattr(transform, token)
    except KeyError:
        return Term.make(token, *args)
    return fun(*args)  # type: ignore[no-any-return]


_PARSERS = {
    _APP: (_polish_parse_tokens, _polish_parse_tokens),
    _JOIN: (_polish_parse_tokens, _polish_parse_tokens),
    _RAND: (_polish_parse_tokens, _polish_parse_tokens),
    _QUOTE: (_polish_parse_tokens,),
    _ABS: (_polish_parse_tokens,),
    _FUN: (_polish_parse_tokens, _polish_parse_tokens),
    _LESS: (_polish_parse_tokens, _polish_parse_tokens),
    _NLESS: (_polish_parse_tokens, _polish_parse_tokens),
    _EQUAL: (_polish_parse_tokens, _polish_parse_tokens),
}


def polish_print(term):
    assert isinstance(term, Term), term
    tokens = []
    _polish_print_tokens(term, tokens)
    return " ".join(tokens)


def _polish_print_tokens(term, tokens):
    if isinstance(term, str):
        tokens.append(term)
    elif isinstance(term, tuple):
        if term[0] is _NVAR:
            tokens.append(term[1])
            pos = 2
        elif term[0] is _IVAR:
            tokens.append(str(term[1]))
            pos = 2
        else:
            tokens.append(term[0])
            pos = 1
        for arg in term[pos:]:
            _polish_print_tokens(arg, tokens)
    elif isinstance(term, int):
        tokens.append(str(term))
    else:
        raise ValueError(term)


################################################################
# S-Expression notation


@memoize_arg
def to_sexpr(term: Term) -> Sexpr:
    """Converts from a python term to a python S-expression."""
    assert isinstance(term, Term), term
    if is_atom(term):
        return term[0]
    if is_nvar(term) or is_ivar(term):
        assert isinstance(term[1], str | int)
        return term[1]
    head: Term = term
    args: list[Sexpr] = []
    while is_app(head):
        args.append(to_sexpr(head[2]))  # type: ignore[arg-type]
        head = head[1]  # type: ignore[assignment]
    if is_nvar(head) or is_ivar(head):
        head = head[1]  # type: ignore[assignment]
    elif head[0] in _keywords:
        args.extend(to_sexpr(arg) for arg in head[-1:0:-1])  # type: ignore[arg-type]
        head = head[0]  # type: ignore[assignment]
    args.append(head)
    args.reverse()
    return tuple(args)


def from_sexpr(sexpr: Sexpr, transform: Transform = identity) -> Term:
    """Converts from a python S-expression to a python term."""
    assert isinstance(transform, Transform), type(transform)

    # Handle atoms and variables.
    if isinstance(sexpr, str):
        if sexpr in _atoms:
            return getattr(transform, sexpr)  # type: ignore[no-any-return]
        if re_keyword.match(sexpr):
            raise ValueError(f"Unrecognized atom: {sexpr}")
        return NVAR(sexpr)  # type: ignore[no-any-return]
    if isinstance(sexpr, int):
        return IVAR(sexpr)  # type: ignore[no-any-return]

    # Handle tuples.
    head = sexpr[0]
    assert isinstance(head, str | int)
    if isinstance(head, str) and head in _keywords:
        arity = _keywords[head]
        head = getattr(transform, head)
        if arity:
            if len(sexpr) < 1 + arity:
                raise ValueError(f"Too few args to {head}: {sexpr}")
            head = head(*(from_sexpr(sexpr[1 + i], transform) for i in range(arity)))
        args = sexpr[1 + arity :]
    elif isinstance(head, int):
        head = IVAR(head)
        args = sexpr[1:]
    else:
        head = NVAR(head)
        args = sexpr[1:]
    for arg in args:
        arg = from_sexpr(arg, transform)
        head = transform.APP(head, arg)
    return head  # type: ignore


def sexpr_print_sexpr(sexpr: Sexpr) -> str:
    """Prints a python S-expression as a string S-expression."""
    if isinstance(sexpr, str):
        return sexpr
    if isinstance(sexpr, int):
        return str(sexpr)
    if isinstance(sexpr, tuple):
        assert len(sexpr) > 1, sexpr
        parts = list(map(sexpr_print_sexpr, sexpr))
        return "({})".format(" ".join(parts))
    raise ValueError(sexpr)


@memoize_arg
def sexpr_print(term: Term) -> str:
    """Prints a python term as a string S-expression."""
    assert isinstance(term, Term), term
    sexpr = to_sexpr(term)
    return sexpr_print_sexpr(sexpr)


_LPAREN = sys.intern("(")
_RPAREN = sys.intern(")")


def _sexpr_parse_tokens(tokens: Iterator[str]) -> Iterator[Sexpr]:
    for token in tokens:
        if token is _LPAREN:
            yield tuple(_sexpr_parse_tokens(tokens))
        elif token is _RPAREN:
            return
        elif re_rank.match(token):
            yield int(token)
        else:
            yield token


def sexpr_parse_sexpr(string: str) -> Sexpr:
    """Parses a string S-expression to a python S-expression."""
    tokens = string.replace("(", " ( ").replace(")", " ) ").split()
    tokens = iter(map(sys.intern, tokens))
    sexpr = next(_sexpr_parse_tokens(tokens))
    try:
        extra = next(tokens)
    except StopIteration:
        pass
    else:
        raise ValueError(f"Extra tokens at end of sexpr: {extra}")
    return sexpr


def sexpr_parse(string: str, transform: Transform = identity) -> Term:
    """Parse a string from S-expression notation to a term.

    Args:
      string: a string in S-expression notation.
      transform: an optional Transform, mapping keyword to builder.

    Returns:
      a term.
    """
    assert isinstance(string, str), type(string)
    assert isinstance(transform, Transform), type(transform)
    sexpr = sexpr_parse_sexpr(string)
    return from_sexpr(sexpr, transform)
