from pomagma.compiler.util import memoize_arg
from pomagma.reducer import engine
from pomagma.reducer.code import S, is_app, sexpr_print
from pomagma.reducer.testing import iter_equations
from pomagma.reducer.testing import s_sk_codes, s_skj_codes
from pomagma.reducer.trace import lazy_print_trace
from pomagma.reducer.trace import trace_deterministic
from pomagma.reducer.trace import trace_nondeterministic
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis
import pytest


# ----------------------------------------------------------------------------
# Parameterized tests

@for_each(iter_equations(['sk', 'quote'], test_id='trace'))
@pytest.mark.timeout(1)
def test_trace_deterministic_equations(code, expected, message):
    with xfail_if_not_implemented():
        result = trace_deterministic(code)
    actual = result['code']
    assert actual == expected, lazy_print_trace(result['trace'], message)


# ----------------------------------------------------------------------------
# Property-based tests

@memoize_arg
def count_S_occurrences(code):
    if is_app(code):
        return count_S_occurrences(code[1]) + count_S_occurrences(code[2])
    elif code is S:
        return 1
    else:
        return 0


@hypothesis.given(s_sk_codes)
@hypothesis.settings(max_examples=1000, max_iterations=10000)
def test_trace_deterministic(code):
    hypothesis.assume(count_S_occurrences(code) <= 1)
    print(sexpr_print(code))
    expected = engine.reduce(code)
    trace = trace_deterministic(code)['trace']
    actual = trace[-1][1]
    assert actual == expected


@pytest.mark.xfail
@hypothesis.given(s_skj_codes)
@hypothesis.settings(max_examples=1000, max_iterations=10000)
def test_trace_nondeterministic(code):
    hypothesis.assume(count_S_occurrences(code) <= 1)
    print(sexpr_print(code))
    expected = engine.reduce(code)
    trace = trace_nondeterministic(code)['trace']
    actual = trace[-1][1]
    assert actual == expected
