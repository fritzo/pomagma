from pomagma.compiler.util import memoize_arg
from pomagma.reducer import engine
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J, VAR, APP
from pomagma.reducer.code import is_app, sexpr_print
from pomagma.reducer.testing import iter_equations
from pomagma.reducer.trace import trace_deterministic
from pomagma.reducer.trace import trace_nondeterministic
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s
import pytest


# ----------------------------------------------------------------------------
# Parameterized tests

@for_each(iter_equations('sk', 'quote'))
def test_trace_deterministic_sk(lhs, rhs):
    print('{} = {}'.format(sexpr_print(lhs), sexpr_print(rhs)))
    lhs = trace_deterministic(lhs)['result']
    rhs = trace_deterministic(rhs)['result']
    assert lhs == rhs


# ----------------------------------------------------------------------------
# Property-based tests

s_vars = s.builds(VAR, s.sampled_from('abcdefghijklmnopqrstuvwxyz'))
s_sk_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
)
s_skj_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
    s.just(J),
)


def s_terms_extend(terms):
    return s.builds(APP, terms, terms)


s_sk_terms = s.recursive(s_sk_atoms, s_terms_extend, max_leaves=100)
s_skj_terms = s.recursive(s_skj_atoms, s_terms_extend, max_leaves=100)


@memoize_arg
def count_S_occurrences(code):
    if is_app(code):
        return count_S_occurrences(code[1]) + count_S_occurrences(code[2])
    elif code is S:
        return 1
    else:
        return 0


@hypothesis.given(s_sk_terms)
@hypothesis.settings(max_examples=1000, max_iterations=10000)
def test_trace_deterministic(code):
    hypothesis.assume(count_S_occurrences(code) <= 1)
    print(sexpr_print(code))
    expected = engine.reduce(code)
    trace = trace_deterministic(code)['trace']
    actual = trace[-1][1]
    assert actual == expected


@pytest.mark.xfail
@hypothesis.given(s_sk_terms)
@hypothesis.settings(max_examples=1000, max_iterations=10000)
def test_trace_nondeterministic(code):
    hypothesis.assume(count_S_occurrences(code) <= 1)
    print(sexpr_print(code))
    expected = engine.reduce(code)
    trace = trace_nondeterministic(code)['trace']
    actual = trace[-1][1]
    assert actual == expected
