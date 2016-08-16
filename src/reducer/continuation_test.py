from pomagma.reducer import continuation
from pomagma.reducer.code import VAR, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import complexity
from pomagma.reducer.continuation import CONT_SET_TOP, make_cont
from pomagma.reducer.continuation import cont_set_from_codes
from pomagma.reducer.testing import iter_equations
from pomagma.reducer.testing import s_codes, s_quoted, s_sk_codes, s_skj_codes
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis

x = VAR('x')
y = VAR('y')
z = VAR('z')

CONT_SET_x = cont_set_from_codes((x,))
CONT_SET_y = cont_set_from_codes((y,))
CONT_SET_S = cont_set_from_codes((S,))


@for_each([x, y, TOP, BOT, I, K, B, C, S, J])
def test_cont_complexity_eq_code_complexity(code):
    cont_set = continuation.cont_set_from_codes((code,))
    assert continuation.cont_set_complexity(cont_set) == complexity(code)


@for_each([
    (TOP, None, None, 1),
    (BOT, None, None, 1),
    (x, None, None, 1),
    (S, None, None, 7),
    (S, None, (x, None), 7 + 1),
    (S, None, (y, (x, None)), 7 + 1 + 1),
    (S, (CONT_SET_TOP, None), None, 7 + 1),
    (S, (CONT_SET_TOP, None), (x, None), 7 + 1 + 1),
    (S, (CONT_SET_TOP, None), (y, (x, None)), 7 + 1 + 1 + 1),
    (S, (CONT_SET_x, None), None, 7 + 1),
    (S, (CONT_SET_x, None), (x, None), 7 + 1 + 1),
    (S, (CONT_SET_x, None), (y, (x, None)), 7 + 1 + 1 + 1),
    (S, (CONT_SET_x, (CONT_SET_TOP, None)), None, 7 + 1 + 1),
    (S, (CONT_SET_x, (CONT_SET_TOP, None)), (x, None), 7 + 1 + 1 + 1),
    (S, (CONT_SET_x, (CONT_SET_TOP, None)), (y, (x, None)), 7 + 1 + 1 + 1 + 1),
    (S, (CONT_SET_S, None), None, 7 + 7),
    (S, (CONT_SET_x | CONT_SET_y, None), None, 7 + 1),
    (S, (CONT_SET_x | CONT_SET_S, None), None, 7 + 7),
])
def test_cont_complexity(code, stack, bound, expected):
    cont = make_cont(code, stack, bound)
    assert continuation.cont_complexity(cont) == expected


@for_each(iter_equations('continuation'))
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
