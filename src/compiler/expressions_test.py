import pytest

from pomagma.compiler.parser import parse_string_to_expr as parse

EXAMPLES = [
    {
        "polish": "x",
        "polish_vars": set(["x"]),
        "polish_consts": set(),
        "polish_terms": set(["x"]),
    },
    {
        "polish": "TOP",
        "polish_vars": set(),
        "polish_consts": set(["TOP"]),
        "polish_terms": set(["TOP"]),
    },
    {
        "polish": "APP TOP x",
        "polish_vars": set(["x"]),
        "polish_consts": set(["TOP"]),
        "polish_terms": set(["x", "TOP", "APP TOP x"]),
    },
    {
        "polish": "APP x TOP",
        "polish_vars": set(["x"]),
        "polish_consts": set(["TOP"]),
        "polish_terms": set(["x", "TOP", "APP x TOP"]),
    },
    {
        "polish": "LESS x TOP",
        "polish_vars": set(["x"]),
        "polish_consts": set(["TOP"]),
        "polish_terms": set(["x", "TOP"]),
    },
    {
        "polish": "LESS APP TOP x y",
        "polish_vars": set(["x", "y"]),
        "polish_consts": set(["TOP"]),
        "polish_terms": set(["x", "y", "TOP", "APP TOP x"]),
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
