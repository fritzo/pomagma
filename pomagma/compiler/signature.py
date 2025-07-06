import re
import sys

from pomagma.compiler.util import intern_keys, memoize_arg

re_const = re.compile("[A-Z]+$")


NARGS_TABLE = intern_keys(
    {
        "UnaryRelation": 1,
        "Equation": 2,
        "BinaryRelation": 2,
        "NullaryFunction": 0,
        "InjectiveFunction": 1,
        "BinaryFunction": 2,
        "SymmetricFunction": 2,
        "Variable": 0,
        "UnaryMeta": 1,
        "BinaryMeta": 2,
        "TernaryMeta": 3,
    }
)

ARITY_TABLE = intern_keys(
    {
        "EQUAL": "Equation",
        "CLOSED": "UnaryRelation",
        "NCLOSED": "UnaryRelation",
        "RETURN": "UnaryRelation",
        "NRETURN": "UnaryRelation",
        "LESS": "BinaryRelation",
        "NLESS": "BinaryRelation",
        "CO": "InjectiveFunction",
        "QUOTE": "InjectiveFunction",
        "APP": "BinaryFunction",
        "COMP": "BinaryFunction",
        "JOIN": "SymmetricFunction",
        "RAND": "SymmetricFunction",
        "VAR": "UnaryMeta",
        "UNKNOWN": "UnaryMeta",
        "OPTIONALLY": "UnaryMeta",
        "NONEGATE": "UnaryMeta",
        "EQUIVALENTLY": "BinaryMeta",
        "FUN": "BinaryMeta",
        "PAIR": "BinaryMeta",
        "ABIND": "TernaryMeta",
        "FIX": "BinaryMeta",
        "FIXES": "BinaryMeta",
    }
)

RELATION_ARITIES = frozenset(
    list(
        map(
            sys.intern,
            [
                "UnaryRelation",
                "Equation",
                "BinaryRelation",
            ],
        )
    )
)

FUNCTION_ARITIES = frozenset(
    list(
        map(
            sys.intern,
            [
                "NullaryFunction",
                "InjectiveFunction",
                "BinaryFunction",
                "SymmetricFunction",
            ],
        )
    )
)

META_ARITIES = frozenset(
    list(
        map(
            sys.intern,
            [
                "UnaryMeta",
                "BinaryMeta",
                "TernaryMeta",
            ],
        )
    )
)


def declare_arity(name: str, arity: str) -> None:
    assert isinstance(name, str)
    assert not is_var(name), name
    assert arity in FUNCTION_ARITIES
    if name in ARITY_TABLE:
        assert ARITY_TABLE[name] == arity, "Cannot change arity"
    else:
        ARITY_TABLE[sys.intern(name)] = arity


@memoize_arg
def is_var(symbol: str) -> bool:
    return re_const.match(symbol) is None


@memoize_arg
def is_fun(symbol: str) -> bool:
    return get_arity(symbol) in FUNCTION_ARITIES


@memoize_arg
def is_term(symbol: str) -> bool:
    return is_var(symbol) or is_fun(symbol)


@memoize_arg
def is_rel(symbol: str) -> bool:
    return get_arity(symbol) in RELATION_ARITIES


@memoize_arg
def is_meta(symbol: str) -> bool:
    return get_arity(symbol) in META_ARITIES


@memoize_arg
def get_arity(symbol: str) -> str:
    if is_var(symbol):
        return "Variable"
    if symbol == "ABS":
        raise NotImplementedError("de Bruijn abstraction ABS is not supported")
    return ARITY_TABLE.get(symbol, "NullaryFunction")


def get_nargs(arity: str) -> int:
    return NARGS_TABLE[arity]


def arity_sort(arity: str) -> tuple[bool, int]:
    return (arity in FUNCTION_ARITIES, get_nargs(arity))


def is_positive(symbol: str) -> bool:
    if symbol == "NLESS":
        return False
    return True


def validate() -> None:
    for symbol, arity in list(ARITY_TABLE.items()):
        assert not is_var(symbol)
        assert arity in NARGS_TABLE
    assert get_arity("x") == "Variable"
    assert get_arity("S") == "NullaryFunction"
