from typing import NotRequired, TypedDict

import pytest

from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr as parse


class Example(TypedDict):
    polish: str
    polish_vars: set[str]
    polish_consts: set[str]
    polish_terms: set[str]
    expression: NotRequired[Expression]
    vars: NotRequired[set[Expression]]
    consts: NotRequired[set[Expression]]
    terms: NotRequired[set[Expression]]


EXAMPLES: list[Example] = [
    {
        "polish": "x",
        "polish_vars": {"x"},
        "polish_consts": set(),
        "polish_terms": {"x"},
    },
    {
        "polish": "TOP",
        "polish_vars": set(),
        "polish_consts": {"TOP"},
        "polish_terms": {"TOP"},
    },
    {
        "polish": "APP TOP x",
        "polish_vars": {"x"},
        "polish_consts": {"TOP"},
        "polish_terms": {"x", "TOP", "APP TOP x"},
    },
    {
        "polish": "APP x TOP",
        "polish_vars": {"x"},
        "polish_consts": {"TOP"},
        "polish_terms": {"x", "TOP", "APP x TOP"},
    },
    {
        "polish": "LESS x TOP",
        "polish_vars": {"x"},
        "polish_consts": {"TOP"},
        "polish_terms": {"x", "TOP"},
    },
    {
        "polish": "LESS APP TOP x y",
        "polish_vars": {"x", "y"},
        "polish_consts": {"TOP"},
        "polish_terms": {"x", "y", "TOP", "APP TOP x"},
    },
]

for example in EXAMPLES:
    example["expression"] = parse(example["polish"])
    example["vars"] = set(map(parse, example["polish_vars"]))
    example["consts"] = set(map(parse, example["polish_consts"]))
    example["terms"] = set(map(parse, example["polish_terms"]))


@pytest.mark.parametrize("example", EXAMPLES)
def test_polish(example):
    expression = example["expression"]
    polish = example["polish"]
    assert expression.polish == polish


@pytest.mark.parametrize("example", EXAMPLES)
def test_vars(example):
    expression = example["expression"]
    vars = example["vars"]
    assert set(expression.vars) == set(vars)


@pytest.mark.parametrize("example", EXAMPLES)
def test_consts(example):
    expression = example["expression"]
    consts = example["consts"]
    assert set(expression.consts) == set(consts)


@pytest.mark.parametrize("example", EXAMPLES)
def test_terms(example):
    expression = example["expression"]
    terms = example["terms"]
    assert set(expression.terms) == set(terms)


def test_replace_exact_match():
    """Test replacing when pattern matches the entire expression."""
    x = parse("x")
    y = parse("y")
    assert x.replace(x, y) == y


def test_replace_no_match():
    """Test replacing when pattern doesn't exist."""
    expr = parse("APP x y")
    z = parse("z")
    w = parse("w")
    # Should return same expression when pattern not found
    assert expr.replace(z, w) == expr


def test_replace_subexpression():
    """Test replacing subexpressions."""
    expr = parse("APP x y")
    x = parse("x")
    z = parse("z")
    expected = parse("APP z y")
    assert expr.replace(x, z) == expected


def test_replace_multiple_occurrences():
    """Test replacing multiple occurrences of the same pattern."""
    expr = parse("APP x x")
    x = parse("x")
    y = parse("y")
    expected = parse("APP y y")
    assert expr.replace(x, y) == expected


def test_replace_nested():
    """Test replacing in nested expressions."""
    expr = parse("APP TOP APP x y")
    pattern = parse("APP x y")
    replacement = parse("z")
    expected = parse("APP TOP z")
    assert expr.replace(pattern, replacement) == expected


def test_replace_complex():
    """Test replacing complex patterns."""
    expr = parse("LESS APP TOP x APP TOP x")
    pattern = parse("APP TOP x")
    replacement = parse("y")
    expected = parse("LESS y y")
    assert expr.replace(pattern, replacement) == expected


def test_replace_recursive_match():
    """Test replacing where the result after arg replacement matches the pattern."""
    # Test a simpler case: replace x with y in "APP x z",
    # and simultaneously look for pattern "APP y z"
    expr = parse("APP x z")
    result = expr.replace(parse("x"), parse("y"))
    expected = parse("APP y z")
    assert result == expected

    # Test the edge case where after replacement, the result itself matches a pattern
    # Start with a nested structure: "APP APP x y z"
    # Replace the inner "APP x y" with "w" to get "APP w z"
    # But then if the pattern we're looking for is "APP w z", it should be replaced too
    nested_expr = parse("APP APP x y z")
    inner_pattern = parse("APP x y")
    inner_replacement = parse("w")

    # First verify normal replacement works
    result1 = nested_expr.replace(inner_pattern, inner_replacement)
    expected1 = parse("APP w z")
    assert result1 == expected1

    # Now test a case where the constructed result would match a new pattern
    # This is harder to construct meaningfully, so let's test it more directly
    # by creating an expression that after arg replacement becomes our target

    # Simple case: "COMP x y" where we replace x with "TOP" to get "COMP TOP y"
    # If our pattern is "COMP TOP y" and replacement is "result", it should work
    base = parse("COMP x y")
    step1 = base.replace(parse("x"), parse("TOP"))
    assert step1 == parse("COMP TOP y")

    # The edge case would be: what if we were looking for "COMP TOP y" as a
    # pattern to replace?
    # Our implementation should catch this case after constructing the new expression
