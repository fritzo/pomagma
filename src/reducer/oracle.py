'''Evaluation of non-computational queries.'''

__all__ = ['try_decide_equal', 'try_decide_less']

from pomagma.compiler.util import memoize_arg
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J, is_app


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


# TODO Add J abstraction rules that would allow J to be added to this list.
# Eg app(J, app(K, I), K) should reduce to J.
_linear_atoms = set([TOP, BOT, I, K, B, C])


@memoize_arg
def is_linear(code):
    if is_app(code):
        return is_linear(code[1]) and is_linear(code[2])
    return code in _linear_atoms


# A short list of some common normal forms.
# TODO initialize this list with, say, 1000 terms proven to be normal.
_normal_forms = set([TOP, BOT, S, J])


def is_normal(code):
    """Weak normality predicate.

    Guarantees that no two distinct normal forms can be Scott equal.

    Inputs:
        code : code in linear normal form.
    Returns:
        weak estimate of whether code is normalized.
        If this returns true, code is indeed normalized.
        If this returns false, code may or may not be normalized.

    """
    return is_linear(code) or code in _normal_forms


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
    if is_normal(x) and is_normal(y):
        return False
    return None


def decide_less_normal(x, y):
    if x is BOT or y is TOP or x is y:
        return True
    if x is TOP or y is BOT:
        return False
    if is_app(x) and is_app(y):
        return TROOL_AND[
            decide_less_normal(x[1], y[1]),
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
    if is_normal(x) and is_normal(y):
        return decide_less_normal(x, y)
    return None
