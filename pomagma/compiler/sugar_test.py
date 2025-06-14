from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.sugar import desugar_expr
from pomagma.util.testing import for_each

EXAMPLES = [
    list(map(parse_string_to_expr, e))
    for e in [
        ("x", "x"),
        ("FUN x x", "I"),
        ("FUN x APP f x", "f"),
        ("FIX x APP f x", "APP Y f"),
        ("PAIR x y", "COMP APP CI y APP CI x"),
        ("ABIND r s COMP r s", "APP A B"),
        ("FIXES BOOL I", "EQUAL APP BOOL I I"),
    ]
]


@for_each(EXAMPLES)
def test_desugar(args):
    (expr, expected) = args
    actual = desugar_expr(expr)
    actual == expected
