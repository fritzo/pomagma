from pomagma.examples.definable_types import trace
from pomagma.util.testing import for_each


@for_each(
    [
        (("base",), {}),
        (("base", "copy"), {}),
        (("base", "bot"), {}),
        (("base", "copy", "bot"), {}),
        (("base", "div"), {}),
        (("base", "swap"), {}),
        (("base", "preconj"), {}),
        (("base", "postconj"), {}),
        (("base", "postconj"), {"fmt": "tiny"}),
        (("base", "compose"), {}),
        (("all",), {"steps": 1}),
    ]
)
def test_trace_runs(args, kwargs):
    trace(*args, **kwargs)
