from pomagma.examples.definable_types import trace
from pomagma.util.testing import for_each


@for_each([
    (('base',), {}),
    (('base', 'copy'), {}),
    (('base', 'copy', 'bot'), {}),
    (('all',), {'steps': 1}),
])
def test_trace_runs(args, kwargs):
    trace(*args, **kwargs)
