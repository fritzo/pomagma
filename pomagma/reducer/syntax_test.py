import hypothesis
import hypothesis.strategies as s

from pomagma.reducer.syntax import (
    ABS,
    APP,
    BOOL,
    BOT,
    CODE,
    EQUAL,
    EVAL,
    FUN,
    IVAR,
    JOIN,
    LESS,
    MAYBE,
    NLESS,
    NUM,
    NVAR,
    PROD,
    QAPP,
    QEQUAL,
    QLESS,
    QQUOTE,
    QUOTE,
    RAND,
    SEMI,
    SUM,
    TOP,
    UNIT,
    A,
    B,
    C,
    I,
    K,
    S,
    V,
    Y,
    anonymize,
    complexity,
    free_vars,
    from_sexpr,
    identity,
    polish_parse,
    polish_print,
    quoted_vars,
    sexpr_parse,
    sexpr_parse_sexpr,
    sexpr_print,
    sexpr_print_sexpr,
    to_sexpr,
)
from pomagma.util.testing import for_each

# ----------------------------------------------------------------------------
# Parameterized tests

x = NVAR("x")
y = NVAR("y")
z = NVAR("z")
i0 = IVAR(0)
i1 = IVAR(1)
i2 = IVAR(2)


@for_each(
    [
        (x, x, i0),
        (y, x, y),
        (i0, x, i1),
        (EVAL, x, EVAL),
        (ABS(i0), x, ABS(i0)),
        (ABS(x), x, ABS(i1)),
        (ABS(ABS(x)), x, ABS(ABS(i2))),
        (APP(x, x), x, APP(i0, i0)),
        (APP(x, ABS(x)), x, APP(i0, ABS(i1))),
        (JOIN(x, y), x, JOIN(i0, y)),
        (JOIN(x, y), y, JOIN(x, i0)),
        (RAND(x, y), x, RAND(i0, y)),
        (RAND(x, y), y, RAND(x, i0)),
        (QUOTE(x), x, QUOTE(i0)),
        (QUOTE(y), x, QUOTE(y)),
        (QUOTE(i0), x, QUOTE(i1)),
    ]
)
def test_anonymize(term, var, expected):
    assert anonymize(term, var) is expected


NVAR_EXAMPLES = [
    (I, [], []),
    (K, [], []),
    (B, [], []),
    (C, [], []),
    (S, [], []),
    (Y, [], []),
    (V, [], []),
    (A, [], []),
    (IVAR(0), [IVAR(0)], []),
    (IVAR(1), [IVAR(1)], []),
    (x, [x], []),
    (APP(I, x), [x], []),
    (APP(x, x), [x], []),
    (APP(x, y), [x, y], []),
    (APP(x, APP(APP(K, y), APP(K, z))), [x, y, z], []),
    (JOIN(I, x), [x], []),
    (JOIN(x, x), [x], []),
    (JOIN(x, y), [x, y], []),
    (RAND(I, x), [x], []),
    (RAND(x, x), [x], []),
    (RAND(x, y), [x, y], []),
    (QUOTE(x), [x], [x]),
    (QUOTE(IVAR(0)), [IVAR(0)], [IVAR(0)]),
    (QUOTE(IVAR(1)), [IVAR(1)], [IVAR(1)]),
    (ABS(QUOTE(IVAR(1))), [IVAR(0)], [IVAR(0)]),
    (QUOTE(APP(x, y)), [x, y], [x, y]),
    (APP(x, QUOTE(y)), [x, y], [y]),
    (ABS(x), [x], []),
    (FUN(x, y), [y], []),
    (FUN(x, x), [], []),
]


@for_each(NVAR_EXAMPLES)
def test_free_vars(term, free, quoted):
    assert free_vars(term) == frozenset(free)


@for_each(NVAR_EXAMPLES)
def test_quoted_vars(term, free, quoted):
    assert quoted_vars(term) == frozenset(quoted)


@for_each(NVAR_EXAMPLES)
def test_quoted_vars_quote(term, free, quoted):
    assert quoted_vars(QUOTE(term)) == frozenset(free)


@for_each(
    [
        (TOP, 0),
        (BOT, 0),
        (x, 1),
        (y, 1),
        (I, 1 + 1),
        (K, 2 + 1),
        (B, 3 + 3),
        (C, 3 + 3),
        (S, 3 + 3),
        (Y, 6),
        (APP(K, I), 1 + max(3, 2)),
        (APP(I, x), 1 + max(2, 1)),
        (JOIN(K, I), max(3, 2)),
        (JOIN(I, x), max(2, 1)),
        (RAND(K, I), 1 + max(3, 2)),
        (RAND(I, x), 1 + max(2, 1)),
        (QUOTE(I), 1 + 2),
        (IVAR(0), 1),
        (ABS(IVAR(0)), 1 + 1),
        (ABS(I), 1 + 2),
        (ABS(K), 1 + 3),
        (FUN(x, x), 1 + max(1, 1)),
        (FUN(x, I), 1 + max(1, 2)),
        (FUN(x, K), 1 + max(1, 3)),
        (APP(APP(S, x), x), 1 + max(1 + max(6, 1), 1)),
        (APP(APP(S, I), x), 1 + max(1 + max(6, 2), 1)),
        (APP(APP(S, I), I), 1 + max(1 + max(6, 2), 2)),
    ]
)
def test_complexity(term, expected):
    assert complexity(term) == expected


EXAMPLES = [
    {"term": TOP, "polish": "TOP", "sexpr": "TOP"},
    {"term": BOT, "polish": "BOT", "sexpr": "BOT"},
    {"term": I, "polish": "I", "sexpr": "I"},
    {"term": K, "polish": "K", "sexpr": "K"},
    {"term": B, "polish": "B", "sexpr": "B"},
    {"term": C, "polish": "C", "sexpr": "C"},
    {"term": S, "polish": "S", "sexpr": "S"},
    {"term": CODE, "polish": "CODE", "sexpr": "CODE"},
    {"term": EVAL, "polish": "EVAL", "sexpr": "EVAL"},
    {"term": QAPP, "polish": "QAPP", "sexpr": "QAPP"},
    {"term": QQUOTE, "polish": "QQUOTE", "sexpr": "QQUOTE"},
    {"term": QEQUAL, "polish": "QEQUAL", "sexpr": "QEQUAL"},
    {"term": QLESS, "polish": "QLESS", "sexpr": "QLESS"},
    {"term": Y, "polish": "Y", "sexpr": "Y"},
    {"term": V, "polish": "V", "sexpr": "V"},
    {"term": A, "polish": "A", "sexpr": "A"},
    {"term": SEMI, "polish": "SEMI", "sexpr": "SEMI"},
    {"term": UNIT, "polish": "UNIT", "sexpr": "UNIT"},
    {"term": BOOL, "polish": "BOOL", "sexpr": "BOOL"},
    {"term": MAYBE, "polish": "MAYBE", "sexpr": "MAYBE"},
    {"term": PROD, "polish": "PROD", "sexpr": "PROD"},
    {"term": SUM, "polish": "SUM", "sexpr": "SUM"},
    {"term": NUM, "polish": "NUM", "sexpr": "NUM"},
    {"term": x, "polish": "x", "sexpr": "x"},
    {"term": APP(K, I), "polish": "APP K I", "sexpr": "(K I)"},
    {"term": JOIN(I, K), "polish": "JOIN I K", "sexpr": "(JOIN I K)"},
    {"term": RAND(I, K), "polish": "RAND I K", "sexpr": "(RAND I K)"},
    {
        "term": QUOTE(APP(I, K)),
        "polish": "QUOTE APP I K",
        "sexpr": "(QUOTE (I K))",
    },
    {
        "term": ABS(IVAR(0)),
        "polish": "ABS 0",
        "sexpr": "(ABS 0)",
    },
    {
        "term": FUN(x, APP(x, x)),
        "polish": "FUN x APP x x",
        "sexpr": "(FUN x (x x))",
    },
    {"term": LESS(K, I), "polish": "LESS K I", "sexpr": "(LESS K I)"},
    {"term": NLESS(K, I), "polish": "NLESS K I", "sexpr": "(NLESS K I)"},
    {"term": EQUAL(K, I), "polish": "EQUAL K I", "sexpr": "(EQUAL K I)"},
]


@for_each(EXAMPLES)
def test_polish_print(example):
    actual = polish_print(example["term"])
    assert actual == example["polish"]


@for_each(EXAMPLES)
def test_polish_parse(example):
    actual = polish_parse(example["polish"])
    assert actual == example["term"]


@for_each(EXAMPLES)
def test_sexpr_print(example):
    actual = sexpr_print(example["term"])
    assert actual == example["sexpr"]


@for_each(EXAMPLES)
def test_sexpr_parse(example):
    actual = sexpr_parse(example["sexpr"])
    assert actual == example["term"]


# ----------------------------------------------------------------------------
# Property-based tests

alphabet = "_abcdefghijklmnopqrstuvwxyz"
s_varnames = s.builds(
    str,
    s.text(alphabet=alphabet, min_size=1),
)
s_ranks = s.integers(min_value=0, max_value=99)
s_vars = s.builds(NVAR, s_varnames)
s_ivars = s.builds(IVAR, s_ranks)
s_atoms = s.one_of(
    s_vars,
    s_ivars,
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
    s.just(Y),
    s.one_of(
        s.just(CODE),
        s.just(EVAL),
        s.just(QAPP),
        s.just(QQUOTE),
        s.just(QEQUAL),
        s.just(QLESS),
    ),
    s.one_of(
        s.just(V),
        s.just(A),
        s.just(UNIT),
        s.just(BOOL),
        s.just(MAYBE),
        s.just(PROD),
        s.just(SUM),
        s.just(NUM),
    ),
)


def s_terms_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(JOIN, terms, terms),
        s.builds(RAND, terms, terms),
        s.builds(QUOTE, terms),
        s.builds(ABS, terms.filter(lambda c: IVAR(0) not in quoted_vars(c))),
        s.builds(FUN, s_vars, terms.filter(lambda c: not quoted_vars(c))),
    )


s_terms = s.recursive(s_atoms, s_terms_extend, max_leaves=100)
s_sexprs = s.builds(to_sexpr, s_terms)


@hypothesis.given(s_terms)
def test_identity_transform(term):
    assert identity(term) is term


@hypothesis.given(s_terms)
def test_free_vars_runs(term):
    free_vars(term)


@hypothesis.given(s_terms)
def test_qutoed_vars_runs(term):
    quoted_vars(term)


@hypothesis.given(s_terms)
def test_complexity_runs(term):
    complexity(term)


@hypothesis.given(s_terms)
@hypothesis.settings(max_examples=1000)
def test_polish_print_parse(term):
    string = polish_print(term)
    assert isinstance(string, str)
    actual_term = polish_parse(string)
    assert actual_term == term


@hypothesis.given(s_terms)
@hypothesis.settings(max_examples=1000)
def test_to_sexpr_from_sexpr(term):
    sexpr = to_sexpr(term)
    actual_term = from_sexpr(sexpr)
    assert actual_term == term


@hypothesis.given(s_sexprs)
@hypothesis.settings(max_examples=1000)
def test_sexpr_print_parse_sexpr(sexpr):
    string = sexpr_print_sexpr(sexpr)
    assert isinstance(string, str)
    actual_sexpr = sexpr_parse_sexpr(string)
    assert actual_sexpr == sexpr


@hypothesis.given(s_terms)
@hypothesis.settings(max_examples=1000)
def test_sexpr_print_parse(term):
    string = sexpr_print(term)
    assert isinstance(string, str)
    actual_term = sexpr_parse(string)
    assert actual_term == term
