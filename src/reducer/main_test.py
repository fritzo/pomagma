from pomagma.reducer import __main__ as main
from pomagma.reducer.code import polish_print, sexpr_print
from pomagma.reducer.testing import iter_equations
from pomagma.util.testing import for_each, skip_if_not_implemented
import pytest


@for_each([
    ('I', 0),
    ('K', 0),
    ('B', 0),
    ('C', 0),
    ('S', 0),
    ('APP I I', 0),
    ('APP I', 1),
    ('APP I I I', 1),
])
def test_reduce_cpp_does_not_crash(code, error_count):
    assert main.reduce_cpp(code) == error_count


@for_each(iter_equations('engine'))
def test_reduce_engine_polish_equations(code, expected_code, message):
    string = polish_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='engine')
    expected_string = polish_print(expected_code)
    assert actual_string == expected_string, message


@for_each(iter_equations('engine'))
def test_reduce_engine_sexpr_equations(code, expected_code, message):
    string = sexpr_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='engine')
    expected_string = sexpr_print(expected_code)
    assert actual_string == expected_string, message


@for_each(iter_equations('continuation'))
def test_reduce_continuatin_polish_equations(code, expected_code, message):
    string = polish_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='continuation')
    expected_string = polish_print(expected_code)
    assert actual_string == expected_string, message


@for_each(iter_equations('continuation'))
def test_reduce_continuatin_sexpr_equations(code, expected_code, message):
    string = sexpr_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='continuation')
    expected_string = sexpr_print(expected_code)
    assert actual_string == expected_string, message


@pytest.mark.timeout(1)
@for_each(iter_equations('de_bruijn'))
def test_reduce_de_bruijn_polish_equations(code, expected_code, message):
    string = polish_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='de_bruijn')
    expected_string = polish_print(expected_code)
    assert actual_string == expected_string, message


@pytest.mark.timeout(1)
@for_each(iter_equations('de_bruijn'))
def test_reduce_de_bruijn_sexpr_equations(code, expected_code, message):
    string = sexpr_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='de_bruijn')
    expected_string = sexpr_print(expected_code)
    assert actual_string == expected_string, message


@pytest.mark.timeout(1)
@for_each(iter_equations('learn'))
def test_reduce_learn_polish_equations(code, expected_code, message):
    string = polish_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='learn')
    expected_string = polish_print(expected_code)
    assert actual_string == expected_string, message


@pytest.mark.timeout(1)
@for_each(iter_equations('learn'))
def test_reduce_learn_sexpr_equations(code, expected_code, message):
    string = sexpr_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='learn')
    expected_string = sexpr_print(expected_code)
    assert actual_string == expected_string, message


@for_each([
    ('(ABS (0 0))', 0),
    ('(ABS (0 0) (ABS (0 0)))', None),
    ('(ABS (0 0) (ABS (0 (0 0))))', None),
])
def test_step(code, expected):
    assert main.step(code) == expected
