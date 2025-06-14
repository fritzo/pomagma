import pytest

from pomagma.reducer import __main__ as main
from pomagma.reducer import bohm, curry
from pomagma.reducer.syntax import polish_print, sexpr_print
from pomagma.reducer.testing import iter_equations
from pomagma.util.testing import skip_if_not_implemented

COMPILE_EXAMPLES = [
    ("I", "(ABS 0)"),
    ("K", "(ABS (ABS 1))"),
    # TODO Add more examples.
]


@pytest.mark.parametrize("curry_string, bohm_string", COMPILE_EXAMPLES)
def test_decompile(curry_string, bohm_string):
    assert main.decompile(curry_string, fmt="sexpr") == bohm_string


@pytest.mark.xfail
@pytest.mark.parametrize("bohm_string, curry_string", COMPILE_EXAMPLES)
def test_compile(bohm_string, curry_string):
    assert main.compile(bohm_string, fmt="sexpr") == curry_string


@pytest.mark.parametrize("term, expected_term, message", iter_equations("curry"))
def test_reduce_curry_polish_equations(term, expected_term, message):
    string = polish_print(term)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine="curry")
        expected_term = curry.convert(expected_term)
    expected_string = polish_print(expected_term)
    assert actual_string == expected_string, message


@pytest.mark.parametrize("term, expected_term, message", iter_equations("curry"))
def test_reduce_curry_sexpr_equations(term, expected_term, message):
    string = sexpr_print(term)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine="curry")
        expected_term = curry.convert(expected_term)
    expected_string = sexpr_print(expected_term)
    assert actual_string == expected_string, message


@pytest.mark.parametrize("term, expected_term, message", iter_equations("bohm"))
def test_reduce_bohm_polish_equations(term, expected_term, message):
    string = polish_print(term)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine="bohm", fmt="polish")
        expected_term = bohm.simplify(expected_term)
    expected_string = polish_print(expected_term)
    assert actual_string == expected_string, message


@pytest.mark.parametrize("term, expected_term, message", iter_equations("bohm"))
def test_reduce_bohm_sexpr_equations(term, expected_term, message):
    string = sexpr_print(term)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine="bohm", fmt="sexpr")
        expected_term = bohm.simplify(expected_term)
    expected_string = sexpr_print(expected_term)
    assert actual_string == expected_string, message


@pytest.mark.parametrize(
    "term, expected",
    [
        ("(ABS (0 0))", 0),
        ("(ABS (0 0) (ABS (0 0)))", None),
        ("(ABS (0 0) (ABS (0 (0 0))))", None),
    ],
)
def test_step(term, expected):
    assert main.step(term) == expected
