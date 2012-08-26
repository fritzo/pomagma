import re


NARGS_TABLE = {
    'Equation': 2,
    'BinaryRelation': 2,
    'NullaryFunction': 0,
    'UnaryFunction': 1,
    'BinaryFunction': 2,
    'SymmetricFunction': 2,
    'Variable': 0,
    }

ARITY_TABLE = {
    'EQUAL': 'Equation',
    'LESS': 'BinaryRelation',
    'NLESS': 'BinaryRelation',
    'CO': 'UnaryFunction',
    'QUOTE': 'UnaryFunction',
    'APP': 'BinaryFunction',
    'COMP': 'BinaryFunction',
    'JOIN': 'SymmetricFunction',
    'RAND': 'SymmetricFunction',
    }


FUNCTION_ARITIES = frozenset([
    'NullaryFunction',
    'UnaryFunction',
    'BinaryFunction',
    'SymmetricFunction',
    ])


def declare_arity(name, arity):
    assert isinstance(name, str)
    assert not is_var(name), name
    assert arity in FUNCTION_ARITIES
    if name in ARITY_TABLE:
        assert ARITY_TABLE[name] == arity, 'Cannot change arity'
    else:
        ARITY_TABLE[name] = arity


def is_var(symbol):
    return re.match('[A-Z]+$', symbol) is None


def is_fun(symbol):
    return get_arity(symbol) in FUNCTION_ARITIES


def get_arity(symbol):
    if is_var(symbol):
        return 'Variable'
    else:
        return ARITY_TABLE.get(symbol, 'NullaryFunction')


def get_nargs(arity):
    return NARGS_TABLE[arity]


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
