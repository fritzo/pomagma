import unification

variable = unification.var


def matches(pattern, expr, match):
    """If expr matches pattern, returns True and sets match dict in-place."""
    _match = unification.unify(expr, pattern)
    if _match is False:
        return False
    assert isinstance(match, dict)
    match.clear()
    match.update(_match)
    return True
