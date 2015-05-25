import re
from pomagma.compiler.util import memoize_arg

re_var = re.compile('[A-Z]+$')


NARGS_TABLE = {
    'UnaryRelation': 1,
    'Equation': 2,
    'BinaryRelation': 2,
    'NullaryFunction': 0,
    'InjectiveFunction': 1,
    'BinaryFunction': 2,
    'SymmetricFunction': 2,
    'Variable': 0,
    'UnaryMeta': 1,
    'BinaryMeta': 2,
    'TernaryMeta': 3,
}

ARITY_TABLE = {
    'EQUAL': 'Equation',
    'CLOSED': 'UnaryRelation',
    'NCLOSED': 'UnaryRelation',
    'RETURN': 'UnaryRelation',
    'NRETURN': 'UnaryRelation',
    'LESS': 'BinaryRelation',
    'NLESS': 'BinaryRelation',
    'CO': 'InjectiveFunction',
    'QUOTE': 'InjectiveFunction',
    'APP': 'BinaryFunction',
    'COMP': 'BinaryFunction',
    'JOIN': 'SymmetricFunction',
    'RAND': 'SymmetricFunction',
    'VAR': 'UnaryMeta',
    'UNKNOWN': 'UnaryMeta',
    'OPTIONALLY': 'UnaryMeta',
    'NONEGATE': 'UnaryMeta',
    'EQUIVALENTLY': 'BinaryMeta',
    'FUN': 'BinaryMeta',
    'ABIND': 'TernaryMeta',
    'FIX': 'BinaryMeta',
    'FIXES': 'BinaryMeta',
}

RELATION_ARITIES = frozenset([
    'UnaryRelation',
    'Equation',
    'BinaryRelation',
])

FUNCTION_ARITIES = frozenset([
    'NullaryFunction',
    'InjectiveFunction',
    'BinaryFunction',
    'SymmetricFunction',
])

META_ARITIES = frozenset([
    'UnaryMeta',
    'BinaryMeta',
    'TernaryMeta',
])


def declare_arity(name, arity):
    assert isinstance(name, str)
    assert not is_var(name), name
    assert arity in FUNCTION_ARITIES
    if name in ARITY_TABLE:
        assert ARITY_TABLE[name] == arity, 'Cannot change arity'
    else:
        ARITY_TABLE[name] = arity


@memoize_arg
def is_var(symbol):
    return re_var.match(symbol) is None


@memoize_arg
def is_fun(symbol):
    return get_arity(symbol) in FUNCTION_ARITIES


@memoize_arg
def is_term(symbol):
    return is_var(symbol) or is_fun(symbol)


@memoize_arg
def is_rel(symbol):
    return get_arity(symbol) in RELATION_ARITIES


@memoize_arg
def is_con(symbol):
    return get_arity(symbol) in META_ARITIES


@memoize_arg
def get_arity(symbol):
    if is_var(symbol):
        return 'Variable'
    else:
        return ARITY_TABLE.get(symbol, 'NullaryFunction')


def get_nargs(arity):
    return NARGS_TABLE[arity]


def arity_sort(arity):
    return (arity in FUNCTION_ARITIES, get_nargs(arity))


def is_positive(symbol):
    if symbol == 'NLESS':
        return False
    else:
        return True


def validate():
    for symbol, arity in ARITY_TABLE.iteritems():
        assert not is_var(symbol)
        assert arity in NARGS_TABLE
    assert get_arity('x') == 'Variable'
    assert get_arity('S') == 'NullaryFunction'
