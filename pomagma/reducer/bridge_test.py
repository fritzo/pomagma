"""Tests for Expression ↔ Term conversions."""

from pomagma.compiler.expressions import Expression
from pomagma.reducer.bridge import expression_to_term, term_to_expression
from pomagma.reducer.syntax import APP, EQUAL, JOIN, NVAR, I, K, S


def test_atom_conversion():
    """Test conversion of atomic expressions."""
    # Expression -> Term -> Expression
    expr = Expression("I")
    term = expression_to_term(expr)
    assert term == I
    back_expr = term_to_expression(term)
    assert back_expr.name == "I"
    assert len(back_expr.args) == 0


def test_variable_conversion():
    """Test conversion of variables."""
    # Expression -> Term -> Expression
    expr = Expression("x")
    term = expression_to_term(expr)
    assert term == NVAR("x")
    back_expr = term_to_expression(term)
    assert back_expr.name == "x"
    assert len(back_expr.args) == 0


def test_app_conversion():
    """Test conversion of application expressions."""
    # Expression -> Term -> Expression
    x_expr = Expression("x")
    y_expr = Expression("y")
    app_expr = Expression("APP", x_expr, y_expr)

    term = expression_to_term(app_expr)
    assert term == APP(NVAR("x"), NVAR("y"))

    back_expr = term_to_expression(term)
    assert back_expr.name == "APP"
    assert len(back_expr.args) == 2
    assert back_expr.args[0].name == "x"
    assert back_expr.args[1].name == "y"


def test_join_conversion():
    """Test conversion of join expressions."""
    # Expression -> Term -> Expression
    i_expr = Expression("I")
    k_expr = Expression("K")
    join_expr = Expression("JOIN", i_expr, k_expr)

    term = expression_to_term(join_expr)
    assert term == JOIN(I, K)

    back_expr = term_to_expression(term)
    assert back_expr.name == "JOIN"
    assert len(back_expr.args) == 2
    assert back_expr.args[0].name == "I"
    assert back_expr.args[1].name == "K"


def test_equal_conversion():
    """Test conversion of equality expressions."""
    # Expression -> Term -> Expression
    x_expr = Expression("x")
    i_expr = Expression("I")
    equal_expr = Expression("EQUAL", x_expr, i_expr)

    term = expression_to_term(equal_expr)
    assert term == EQUAL(NVAR("x"), I)

    back_expr = term_to_expression(term)
    assert back_expr.name == "EQUAL"
    assert len(back_expr.args) == 2
    assert back_expr.args[0].name == "x"
    assert back_expr.args[1].name == "I"


def test_complex_expression():
    """Test conversion of more complex nested expressions."""
    # APP(APP(S, K), I)
    s_expr = Expression("S")
    k_expr = Expression("K")
    i_expr = Expression("I")
    sk_expr = Expression("APP", s_expr, k_expr)
    ski_expr = Expression("APP", sk_expr, i_expr)

    term = expression_to_term(ski_expr)
    expected_term = APP(APP(S, K), I)
    assert term == expected_term

    back_expr = term_to_expression(term)
    assert back_expr.name == "APP"
    assert back_expr.args[0].name == "APP"
    assert back_expr.args[0].args[0].name == "S"
    assert back_expr.args[0].args[1].name == "K"
    assert back_expr.args[1].name == "I"


def test_round_trip_consistency():
    """Test that Expression -> Term -> Expression preserves semantics."""
    # Create various test expressions
    test_expressions = [
        Expression("I"),
        Expression("x"),
        Expression("APP", Expression("I"), Expression("x")),
        Expression("JOIN", Expression("I"), Expression("K")),
        Expression("EQUAL", Expression("x"), Expression("I")),
    ]

    for expr in test_expressions:
        term = expression_to_term(expr)
        back_expr = term_to_expression(term)

        # Check that the structure is preserved
        assert back_expr.name == expr.name
        assert len(back_expr.args) == len(expr.args)

        # For simple cases, check Polish notation equivalence
        if not expr.args or all(not arg.args for arg in expr.args):
            assert back_expr.polish == expr.polish
