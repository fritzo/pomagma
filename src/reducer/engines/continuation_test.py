from pomagma.reducer.code import NVAR, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import complexity
from pomagma.reducer.engines import continuation
from pomagma.reducer.engines.continuation import CONT_SET_TOP, make_cont
from pomagma.reducer.engines.continuation import cont_set_from_codes
from pomagma.reducer.testing import iter_equations
from pomagma.reducer.testing import s_codes, s_quoted, s_sk_codes, s_skj_codes
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')

CONT_SET_x = cont_set_from_codes((x,))
CONT_SET_y = cont_set_from_codes((y,))
CONT_SET_S = cont_set_from_codes((S,))


@for_each([x, y, TOP, BOT, I, K, B, C, S])
def test_cont_complexity_eq_code_complexity(code):
    cont_set = continuation.cont_set_from_codes((code,))
    assert continuation.cont_set_complexity(cont_set) == complexity(code)


@for_each([
    (TOP, None, None, 0),
    (BOT, None, None, 0),
    (x, None, None, 1),
    (S, None, None, 6),
    (S, None, (x, None), 1 + max(6, 1)),
    (S, None, (y, (x, None)), 6 + 2),
    (S, (CONT_SET_TOP, None), None, 1 + max(6, 0)),
    (S, (CONT_SET_TOP, None), (x, None), 1 + max(6, 0) + 1),
    (S, (CONT_SET_TOP, None), (y, (x, None)), 1 + max(6, 0) + 2),
    (S, (CONT_SET_x, None), None, 1 + max(6, 1)),
    (S, (CONT_SET_x, None), (x, None), 1 + max(6, 1) + 1),
    (S, (CONT_SET_x, None), (y, (x, None)), 1 + max(6, 1) + 2),
    (S, (CONT_SET_x, (CONT_SET_TOP, None)), None, 1 + max(1 + max(6, 1), 0)),
    (S, (CONT_SET_S, None), None, 1 + max(6, 6)),
    (x, (CONT_SET_x | CONT_SET_y, None), None, 1 + max(1, max(1, 1))),
    (x, (CONT_SET_x | CONT_SET_S, None), None, 1 + max(1, max(1, 6))),
    (S, (CONT_SET_x | CONT_SET_y, None), None, 1 + max(6, max(1, 1))),
    (S, (CONT_SET_x | CONT_SET_S, None), None, 1 + max(6, max(1, 6))),
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
