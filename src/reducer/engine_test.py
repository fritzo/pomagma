from pomagma.reducer import engine
from pomagma.reducer.code import VAR, I
from pomagma.reducer.testing import iter_equations, s_codes, s_quoted
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis

BUDGET = 10000

x = VAR('x')
y = VAR('y')
z = VAR('z')


@for_each([
    (None, None, 0),
    (None, None, 0),
    (None, (x, None), 3),
    (None, (y, (x, None)), 6),
    ((I, None), None, 2),
    ((I, None), (x, None), 2 + 3),
    ((I, None), (y, (x, None)), 2 + 6),
    ((x, None), None, 3),
    ((x, None), (x, None), 3 + 3),
    ((x, None), (y, (x, None)), 3 + 6),
    ((x, (I, None)), None, 5),
    ((x, (I, None)), (x, None), 5 + 3),
    ((x, (I, None)), (y, (x, None)), 5 + 6),
])
def test_context_complexity(stack, bound, expected):
    context = engine.Context(stack=stack, bound=bound)
    assert engine.context_complexity(context) == expected


@for_each(iter_equations(['sk', 'join', 'quote', 'types'], test_id='engine'))
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
