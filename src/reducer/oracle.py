'''Evaluation of non-computational queries.'''

from pomagma.reducer.code import TOP, BOT, is_atom


def try_decide_equal(x, y):
    """Weak oracle approximating Scott equality.

    Inputs:
      x, y : code or None
    Returns:
      True, False, or None

    """
    if x is None or y is None:
        return None
    if x is y:
        return True
    if is_atom(x) and is_atom(y):
        return False
    return None


def try_decide_less(x, y):
    """Weak oracle approximating Scott ordering.

    Inputs:
      x, y : code or None
    Returns:
      True, False, or None

    """
    if x is BOT or y is TOP:
        return True
    if x is TOP and y is BOT:
        return False
    if x is not None and x is y:
        return True
    return None
