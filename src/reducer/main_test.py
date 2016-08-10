from pomagma.reducer import __main__ as main
from pomagma.reducer.code import polish_print, sexpr_print
from pomagma.reducer.testing import iter_equations
from pomagma.util.testing import for_each, skip_if_not_implemented


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


@for_each(iter_equations(['sk', 'join', 'quote'], test_id='engine'))
def test_reduce_engine_polish_equations(code, expected_code, message):
    string = polish_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='engine')
    expected_string = polish_print(expected_code)
    assert actual_string == expected_string, message


@for_each(iter_equations(['sk', 'join', 'quote'], test_id='engine'))
def test_reduce_engine_sexpr_equations(code, expected_code, message):
    string = sexpr_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='engine')
    expected_string = sexpr_print(expected_code)
    assert actual_string == expected_string, message


@for_each(iter_equations(['sk', 'join'], test_id='continuation'))
def test_reduce_continuatin_polish_equations(code, expected_code, message):
    string = polish_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='continuation')
    expected_string = polish_print(expected_code)
    assert actual_string == expected_string, message


@for_each(iter_equations(['sk', 'join'], test_id='continuation'))
def test_reduce_continuatin_sexpr_equations(code, expected_code, message):
    string = sexpr_print(code)
    with skip_if_not_implemented():
        actual_string = main.reduce(string, engine='continuation')
    expected_string = sexpr_print(expected_code)
    assert actual_string == expected_string, message
