'''Evaluation of non-computational queries.'''

__all__ = ['try_decide_equal', 'try_decide_less']

from pomagma.compiler.util import memoize_arg
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J, APP
from pomagma.reducer.code import is_app

TROOL_AND = {
    (True, True): True,
    (True, False): False,
    (True, None): None,
    (False, True): False,
    (False, False): False,
    (False, None): False,
    (None, True): None,
    (None, False): False,
    (None, None): None,
}

TROOL_OR = {
    (True, True): True,
    (True, False): True,
    (True, None): True,
    (False, True): True,
    (False, False): False,
    (False, None): None,
    (None, True): True,
    (None, False): None,
    (None, None): None,
}

LINEAR_ATOMS = set([TOP, BOT, I, K, B, C, J])  # TODO would variables be ok?
NORMAL_FORMS = set([S])  # TODO initialize with ~1000 codes.


@memoize_arg
def is_linear(code):
    if is_app(code):
        return is_linear(code[1]) and is_linear(code[2])
    return code in LINEAR_ATOMS


def try_match_join(code):
    if code is J:
        return K, APP(K, I)
    if is_app(code):
        if code[1] is J:
            return APP(K, code[2]), I
        elif is_app(code[1]) and code[1][1] is J:
            return code[1][2], code[2]
    return None


def try_decide_normal(code):
    if is_linear(code):
        return True
    if code in NORMAL_FORMS:
        return True
    return None


def try_decide_equal(x, y):
    """Weak oracle approximating Scott equality.

    Inputs:
        x, y : either None or code in linear normal form
    Returns:
        True, False, or None

    """
    if x is None or y is None:
        return None
    if x is y:
        return True
    if try_decide_normal(x) and try_decide_normal(y):
        return False
    return None


def decide_less_normal(x, y):
    """Strong oracle for Scott ordering on normal codes.

    Inputs:
        x, y : normal codes.
    Returns:
        True, False, or None

    """
    if x is BOT or y is TOP or x is y:
        return True
    match = try_match_join(x)
    if match is not None:
        return TROOL_AND[decide_less_normal(match[0], y),
                         decide_less_normal(match[1], y)]
    match = try_match_join(y)
    if match is not None:
        return TROOL_OR[decide_less_normal(x, match[0]),
                        decide_less_normal(x, match[1])]
    if x is TOP or y is BOT:
        return False
    if is_app(x) and is_app(y):
        return TROOL_AND[decide_less_normal(x[1], y[1]),
                         decide_less_normal(x[2], y[2])]
    return False


def try_decide_less(x, y):
    """Weak oracle approximating Scott ordering.

    Inputs:
        x, y : either None or code in linear normal form
    Returns:
        True, False, or None

    """
    if x is BOT or y is TOP:
        return True
    if x is None or y is None:
        return None
    if x is y:
        return True
    if try_decide_normal(x) and try_decide_normal(y):
        return decide_less_normal(x, y)
    return None
