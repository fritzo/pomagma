from pomagma.reducer import continuation
from pomagma.reducer.code import VAR, I, S
from pomagma.reducer.testing import iter_equations
from pomagma.reducer.testing import s_codes, s_quoted, s_sk_codes, s_skj_codes
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis

x = VAR('x')
y = VAR('y')
z = VAR('z')


@for_each([
    (S, None, None, 1 + 0 + 0),
    (x, None, None, 2 + 0 + 0),
    (S, None, (x, None), 1 + 0 + 3),
    (S, None, (y, (x, None)), 1 + 0 + 6),
    (S, (I, None), None, 1 + 2 + 0),
    (S, (I, None), (x, None), 1 + 2 + 3),
    (S, (I, None), (y, (x, None)), 1 + 2 + 6),
    (S, (x, None), None, 1 + 3 + 0),
    (S, (x, None), (x, None), 1 + 3 + 3),
    (S, (x, None), (y, (x, None)), 1 + 3 + 6),
    (S, (x, (I, None)), None, 1 + 5 + 0),
    (S, (x, (I, None)), (x, None), 1 + 5 + 3),
    (S, (x, (I, None)), (y, (x, None)), 1 + 5 + 6),
])
def test_cont_complexity(code, stack, bound, expected):
    cont = continuation.make_cont(code, stack, bound)
    assert continuation.cont_complexity(cont) == expected


@for_each(iter_equations(['sk', 'join', 'quote'], test_id='continuation'))
def test_reduce_equations(code, expected, message):
    with xfail_if_not_implemented():
        actual = continuation.reduce(code)
    assert actual == expected, message


@hypothesis.given(s_sk_codes)
def test_simplify_runs_sk(code):
    with xfail_if_not_implemented():
        continuation.simplify(code)


@hypothesis.given(s_skj_codes)
def test_simplify_runs_skj(code):
    with xfail_if_not_implemented():
        continuation.simplify(code)


@hypothesis.given(s_codes)
def test_simplify_runs(code):
    with xfail_if_not_implemented():
        continuation.simplify(code)


@hypothesis.given(s_quoted)
def test_simplify_runs_quoted(quoted):
    with xfail_if_not_implemented():
        continuation.simplify(quoted)
