from pomagma.reducer import engine
from pomagma.reducer.code import NVAR, I
from pomagma.reducer.testing import iter_equations, s_codes, s_quoted
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis

BUDGET = 10000

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


@for_each([
    (None, None, 0),
    (None, None, 0),
    (None, (x, None), 1),
    (None, (y, (x, None)), 1 + 1),
    ((I, None), None, 2),
    ((I, None), (x, None), 2 + 1),
    ((I, None), (y, (x, None)), 2 + 1 + 1),
    ((x, None), None, 1),
    ((x, None), (x, None), 1 + 1),
    ((x, None), (y, (x, None)), 1 + 1 + 1),
    ((x, (I, None)), None, 1 + 2),
    ((x, (I, None)), (x, None), 1 + 2 + 1),
    ((x, (I, None)), (y, (x, None)), 1 + 2 + 1 + 1),
])
def test_context_complexity(stack, bound, expected):
    context = engine.Context(stack=stack, bound=bound)
    assert engine.context_complexity(context) == expected


@for_each(iter_equations('engine'))
def test_trace_reduce_equations(code, expected, message):
    with xfail_if_not_implemented():
        actual = engine.reduce(code, BUDGET)
    assert actual == expected, message


@hypothesis.given(s_codes)
def test_simplify_runs(code):
    with xfail_if_not_implemented():
        engine.simplify(code)


@hypothesis.given(s_quoted)
def test_simplify_runs_quoted(quoted):
    with xfail_if_not_implemented():
        engine.simplify(quoted)
