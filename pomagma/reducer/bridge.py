"""Bridge module for converting between Expression and Term representations."""

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.reducer import syntax
from pomagma.reducer.curry import convert
from pomagma.reducer.syntax import Term


def expression_to_term(expr: Expression) -> Term:
    """Convert an Expression to a Term.

    Args:
        expr: Expression to convert

    Returns:
        Equivalent Term representation
    """
    name = expr.name
    args = expr.args

    # Handle nullary functions (atoms and variables)
    if not args:
        if expr.is_var():
            return syntax.NVAR(name)
        # Use polish notation for atoms to ensure they parse correctly
        result = syntax.polish_parse(name)
        assert isinstance(result, Term)
        return result

    # Handle binary functions
    if len(args) == 2:
        lhs_term = expression_to_term(args[0])
        rhs_term = expression_to_term(args[1])

        if name == "APP":
            return syntax.APP(lhs_term, rhs_term)
        if name == "COMP":
            # COMP is not in reducer.syntax, fall back to polish
            result = syntax.polish_parse(expr.polish)
            assert isinstance(result, Term)
            return result
        if name == "JOIN":
            return syntax.JOIN(lhs_term, rhs_term)
        if name == "RAND":
            return syntax.RAND(lhs_term, rhs_term)
        if name == "EQUAL":
            return syntax.EQUAL(lhs_term, rhs_term)
        if name == "LESS":
            return syntax.LESS(lhs_term, rhs_term)
        if name == "NLESS":
            return syntax.NLESS(lhs_term, rhs_term)
        # Fall back to polish notation for unknown binary functions
        result = syntax.polish_parse(expr.polish)
        assert isinstance(result, Term)
        return result

    # Handle unary functions
    if len(args) == 1:
        arg_term = expression_to_term(args[0])

        if name == "QUOTE":
            return syntax.QUOTE(arg_term)
        if name == "ABS":
            # ABS requires special handling for de Bruijn indices
            result = syntax.polish_parse(expr.polish)
            assert isinstance(result, Term)
            return result
        # Fall back to polish notation for unknown unary functions
        result = syntax.polish_parse(expr.polish)
        assert isinstance(result, Term)
        return result

    # Fall back to polish notation for complex cases
    result = syntax.polish_parse(expr.polish)
    assert isinstance(result, Term)
    return result


def term_to_expression(term: Term) -> Expression:
    """Convert a Term to an Expression.

    Args:
        term: Term to convert

    Returns:
        Equivalent Expression representation
    """
    term = convert(term)
    if syntax.is_atom(term):
        return Expression(term[0])
    if syntax.is_nvar(term):
        return Expression(str(term[1]))
    if syntax.is_app(term):
        lhs_expr = term_to_expression(term[1])  # type: ignore[arg-type]
        rhs_expr = term_to_expression(term[2])  # type: ignore[arg-type]
        return Expression("APP", lhs_expr, rhs_expr)
    if syntax.is_join(term):
        lhs_expr = term_to_expression(term[1])  # type: ignore[arg-type]
        rhs_expr = term_to_expression(term[2])  # type: ignore[arg-type]
        return Expression("JOIN", lhs_expr, rhs_expr)
    if syntax.is_equal(term):
        lhs_expr = term_to_expression(term[1])  # type: ignore[arg-type]
        rhs_expr = term_to_expression(term[2])  # type: ignore[arg-type]
        return Expression("EQUAL", lhs_expr, rhs_expr)
    if syntax.is_quote(term):
        arg_expr = term_to_expression(term[1])  # type: ignore[arg-type]
        return Expression("QUOTE", arg_expr)
    # Fall back to polish notation for complex cases
    return parse_string_to_expr(syntax.polish_print(term))
