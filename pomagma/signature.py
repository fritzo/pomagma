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
    'QUOTE': 'UnaryFunction',
    'APP': 'BinaryFunction',
    'COMP': 'BinaryFunction',
    'JOIN': 'SymmetricFunction',
    'RAND': 'SymmetricFunction',
    }


def is_var(symbol):
    return re.match('[a-z_]', symbol[-1]) is not None


for symbol in ARITY_TABLE:
    assert not is_var(symbol)


def get_arity(symbol):
    if is_var(symbol):
        return 'Variable'
    else:
        return ARITY_TABLE.get(symbol, 'NullaryFunction')


def get_nargs(arity):
    return NARGS_TABLE[arity]
