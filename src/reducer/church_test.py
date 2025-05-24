import hypothesis

from pomagma.reducer.church import convert
from pomagma.reducer.syntax import sexpr_parse, sexpr_print
from pomagma.reducer.testing import s_terms
from pomagma.util.testing import for_each


@for_each(
    [
        ("(ABS 0)", "(FUN a a)"),
        ("(ABS (ABS (1 0))", "(FUN a (FUN b (a b)))"),
        ("(FUN a (ABS (a 0))", "(FUN a (FUN b (a b)))"),
        ("(ABS (FUN b (0 b))", "(FUN a (FUN b (a b)))"),
        ("(ABS (0 0 1 2))", "(FUN a (a a 0 1))"),
        ("(ABS 1)", "(FUN a 0)"),
        ("(ABS (JOIN 0 1))", "(FUN a (JOIN a 0))"),
        ("(QUOTE (ABS 0))", "(QUOTE (FUN a a))"),
    ]
)
def test_nominalize(term, expected):
    actual = sexpr_print(convert(sexpr_parse(term)))
    assert actual == expected


@hypothesis.given(s_terms)
def test_nominalize_runs(term):
    convert(term)
