from pomagma.reducer.code import (
    APP, JOIN, NVAR, IVAR, FUN, LET, ABIND, RVAR, SVAR, SLICEBEG, SLICEEND,
    QUOTE, CODE, EVAL, QAPP, QQUOTE, EQUAL, LESS,
    TOP, BOT, I, K, B, C, S, V, A, UNIT, BOOL, MAYBE, PROD, SUM, NUM,
    free_vars, complexity, polish_parse, polish_print,
    sexpr_parse, sexpr_print, sexpr_parse_sexpr, sexpr_print_sexpr,
    to_sexpr, from_sexpr,
)

from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s


# ----------------------------------------------------------------------------
# Parameterized tests

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


@for_each([
    (I, []),
    (K, []),
    (B, []),
    (C, []),
    (S, []),
    (A, []),
    (ABIND(x), [x]),
    (RVAR(0), []),
    (SVAR(0), []),
    (IVAR(0), []),
    (IVAR(1), []),
    (x, [x]),
    (APP(I, x), [x]),
    (APP(x, x), [x]),
    (APP(x, y), [x, y]),
    (APP(x, APP(APP(K, y), APP(K, z))), [x, y, z]),
    (JOIN(I, x), [x]),
    (JOIN(x, x), [x]),
    (JOIN(x, y), [x, y]),
    (QUOTE(x), [x]),
    (QUOTE(APP(x, y)), [x, y]),
    (APP(x, QUOTE(y)), [x, y]),
    (SLICEBEG(x), [x]),
    (SLICEEND(x), [x]),
])
def test_free_vars(code, free):
    assert free_vars(code) == frozenset(free)


@for_each([
    (TOP, 0),
    (BOT, 0),
    (x, 1),
    (y, 1),
    (I, 1 + 1),
    (K, 2 + 1),
    (B, 3 + 3),
    (C, 3 + 3),
    (S, 3 + 3),
    (APP(K, I), 1 + max(3, 2)),
    (APP(I, x), 1 + max(2, 1)),
    (JOIN(K, I), max(3, 2)),
    (JOIN(I, x), max(2, 1)),
    (QUOTE(I), 1 + 2),
    (FUN(x, x), 1 + max(1, 1)),
    (FUN(x, I), 1 + max(1, 2)),
    (FUN(x, K), 1 + max(1, 3)),
    (LET(x, x, x), 1 + max(1, 1, 1)),
    (LET(x, I, x), 1 + max(1, 2, 1)),
    (LET(x, K, x), 1 + max(1, 3, 1)),
    (APP(APP(S, x), x), 1 + max(1 + max(6, 1), 1)),
    (APP(APP(S, I), x), 1 + max(1 + max(6, 2), 1)),
    (APP(APP(S, I), I), 1 + max(1 + max(6, 2), 2)),
])
def test_complexity(code, expected):
    assert complexity(code) == expected


EXAMPLES = [
    {'code': TOP, 'polish': 'TOP', 'sexpr': 'TOP'},
    {'code': BOT, 'polish': 'BOT', 'sexpr': 'BOT'},
    {'code': I, 'polish': 'I', 'sexpr': 'I'},
    {'code': K, 'polish': 'K', 'sexpr': 'K'},
    {'code': B, 'polish': 'B', 'sexpr': 'B'},
    {'code': C, 'polish': 'C', 'sexpr': 'C'},
    {'code': S, 'polish': 'S', 'sexpr': 'S'},
    {'code': CODE, 'polish': 'CODE', 'sexpr': 'CODE'},
    {'code': EVAL, 'polish': 'EVAL', 'sexpr': 'EVAL'},
    {'code': QAPP, 'polish': 'QAPP', 'sexpr': 'QAPP'},
    {'code': QQUOTE, 'polish': 'QQUOTE', 'sexpr': 'QQUOTE'},
    {'code': EQUAL, 'polish': 'EQUAL', 'sexpr': 'EQUAL'},
    {'code': LESS, 'polish': 'LESS', 'sexpr': 'LESS'},
    {'code': V, 'polish': 'V', 'sexpr': 'V'},
    {'code': A, 'polish': 'A', 'sexpr': 'A'},
    {'code': UNIT, 'polish': 'UNIT', 'sexpr': 'UNIT'},
    {'code': BOOL, 'polish': 'BOOL', 'sexpr': 'BOOL'},
    {'code': MAYBE, 'polish': 'MAYBE', 'sexpr': 'MAYBE'},
    {'code': PROD, 'polish': 'PROD', 'sexpr': 'PROD'},
    {'code': SUM, 'polish': 'SUM', 'sexpr': 'SUM'},
    {'code': NUM, 'polish': 'NUM', 'sexpr': 'NUM'},
    {'code': x, 'polish': 'x', 'sexpr': 'x'},
    {'code': APP(K, I), 'polish': 'APP K I', 'sexpr': '(K I)'},
    {'code': JOIN(I, K), 'polish': 'JOIN I K', 'sexpr': '(JOIN I K)'},
    {
        'code': QUOTE(APP(I, K)),
        'polish': 'QUOTE APP I K',
        'sexpr': '(QUOTE (I K))',
    },
    {
        'code': FUN(x, APP(x, x)),
        'polish': 'FUN x APP x x',
        'sexpr': '(FUN x (x x))',
    },
    {
        'code': LET(x, I, APP(I, I)),
        'polish': 'LET x I APP I I',
        'sexpr': '(LET x I (I I))',
    },
    {
        'code': ABIND(APP(APP(B, RVAR(0)), SVAR(0))),
        'polish': 'ABIND APP APP B RVAR 0 SVAR 0',
        'sexpr': '(ABIND (B (RVAR 0) (SVAR 0)))',
    },
    {
        'code': APP(SLICEBEG(APP(x, y)), z),
        'polish': 'APP SLICEBEG APP x y z',
        'sexpr': '(SLICEBEG (x y) z)',
    },
    {
        'code': APP(SLICEEND(APP(x, y)), z),
        'polish': 'APP SLICEEND APP x y z',
        'sexpr': '(SLICEEND (x y) z)',
    },
]


@for_each(EXAMPLES)
def test_polish_print(example):
    actual = polish_print(example['code'])
    assert actual == example['polish']


@for_each(EXAMPLES)
def test_polish_parse(example):
    actual = polish_parse(example['polish'])
    assert actual == example['code']


@for_each(EXAMPLES)
def test_sexpr_print(example):
    actual = sexpr_print(example['code'])
    assert actual == example['sexpr']


@for_each(EXAMPLES)
def test_sexpr_parse(example):
    actual = sexpr_parse(example['sexpr'])
    assert actual == example['code']


# ----------------------------------------------------------------------------
# Property-based tests

alphabet = '_abcdefghijklmnopqrstuvwxyz'
s_varnames = s.builds(
    str,
    s.text(alphabet=alphabet, min_size=1, average_size=5),
)
s_ranks = s.integers(min_value=0, max_value=99)
s_vars = s.builds(NVAR, s_varnames)
s_ivars = s.builds(IVAR, s_ranks)
s_rvars = s.builds(RVAR, s_ranks)
s_svars = s.builds(SVAR, s_ranks)
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
    s.one_of(
        s.just(CODE),
        s.just(EVAL),
        s.just(QAPP),
        s.just(QQUOTE),
        s.just(EQUAL),
        s.just(LESS),
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
        s_rvars,
        s_svars,
    ),
)


def s_codes_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(JOIN, terms, terms),
        s.builds(QUOTE, terms),
        s.builds(FUN, s_vars, terms),
        s.builds(LET, s_vars, terms, terms),
        s.builds(ABIND, terms),
    )


s_codes = s.recursive(s_atoms, s_codes_extend, max_leaves=100)
s_sexprs = s.builds(to_sexpr, s_codes)


@hypothesis.given(s_codes)
def test_free_vars_runs(code):
    free_vars(code)


@hypothesis.given(s_codes)
def test_complexity_runs(code):
    complexity(code)


@hypothesis.given(s_codes)
@hypothesis.settings(max_examples=1000)
def test_polish_print_parse(code):
    string = polish_print(code)
    assert isinstance(string, str)
    actual_code = polish_parse(string)
    assert actual_code == code


@hypothesis.given(s_codes)
@hypothesis.settings(max_examples=1000)
def test_to_sexpr_from_sexpr(code):
    sexpr = to_sexpr(code)
    actual_code = from_sexpr(sexpr)
    assert actual_code == code


@hypothesis.given(s_sexprs)
@hypothesis.settings(max_examples=1000)
def test_sexpr_print_parse_sexpr(sexpr):
    string = sexpr_print_sexpr(sexpr)
    assert isinstance(string, str)
    actual_sexpr = sexpr_parse_sexpr(string)
    assert actual_sexpr == sexpr


@hypothesis.given(s_codes)
@hypothesis.settings(max_examples=1000)
def test_sexpr_print_parse(code):
    string = sexpr_print(code)
    assert isinstance(string, str)
    actual_code = sexpr_parse(string)
    assert actual_code == code
