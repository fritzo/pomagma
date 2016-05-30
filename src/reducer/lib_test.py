from pomagma.reducer import lib
from pomagma.reducer.sugar import as_code, app
import pytest


# ----------------------------------------------------------------------------
# Tests for intro forms

INTRO_FORM_EXAMPLES = [
    ('void', lambda x: x),
    ('true', lambda x, y: x),
    ('false', lambda x, y: y),
    ('none', lambda f, g: f),
    ('some', lambda x, f, g: app(g, x)),
    ('pair', lambda x, y, f: app(f, x, y)),
    ('inl', lambda x, f, g: app(f, x)),
    ('inr', lambda y, f, g: app(g, y)),
    ('zero', lambda z, s: z),
    ('succ', lambda n, z, s: app(s, n)),
    ('nil', lambda n, c: n),
    ('cons', lambda head, tail, n, c: app(c, head, tail)),
]


@pytest.mark.parametrize('name,native', INTRO_FORM_EXAMPLES)
def test_intro_forms(name, native):
    assert as_code(getattr(lib, name)) == as_code(native)
