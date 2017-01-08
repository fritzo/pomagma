from pomagma.reducer.huet98 import Presentation, eta_expand, make_combinator
from pomagma.util.testing import for_each, xfail_if_not_implemented


@for_each([
    (
        make_combinator(1, 0),
        make_combinator(2, 0, ('_I', 1)),
    ),
    (
        make_combinator(5, 3),
        make_combinator(6, 3, ('_I', 5)),
    ),
    (
        make_combinator(2, 0, ('_I', 1)),
        make_combinator(3, 0, ('_I', 1), ('_I', 2)),
    ),
    (
        make_combinator(2, 1, ('X', 0, 1)),
        make_combinator(3, 1, ('X', 0, 1), ('_I', 2)),
    ),
])
def test_eta_expand(comb, expected):
    assert eta_expand(comb) == expected


def test_fixed_points():
    """Example from huet1998regular pp. 6."""
    p = Presentation()
    # Y f = f(Y(f))
    p.define('Y', make_combinator(1, 0, ('Y', 0)))
    # Z0 f = f(Z1(f))
    p.define('Z1', make_combinator(1, 0, ('Z0', 0)))
    # Z1 f = f(Z0(f))
    p.define('Z0', make_combinator(1, 0, ('Z1', 0)))
    with xfail_if_not_implemented():
        assert p.decide_equal('Y', 'Z0')
        assert p.decide_equal('Y', 'Z1')
        assert p.decide_equal('Z0', 'Z1')


def test_J_equals_I():
    """Example from huet1998regular pp. 8."""
    p = Presentation()
    # J x y = (x (J y))
    p.define('J', make_combinator(2, 0, ('J', 1)))
    # I x = x
    p.define('I', make_combinator(1, 0))
    with xfail_if_not_implemented():
        assert p.decide_equal('I', 'J')
