from pomagma.reducer.code import CODE, EVAL, QAPP, QQUOTE, EQUAL, LESS
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import V, A, UNIT, BOOL, MAYBE, PROD, SUM, NUM
from pomagma.reducer.code import VAR, APP, QUOTE, FUN, LET
from pomagma.reducer.code import free_vars, complexity
from pomagma.reducer.code import polish_parse, polish_print
from pomagma.reducer.code import sexpr_parse, sexpr_print
from pomagma.reducer.code import sexpr_parse_sexpr, sexpr_print_sexpr
from pomagma.reducer.code import to_sexpr, from_sexpr
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s


# ----------------------------------------------------------------------------
# Parameterized tests

x = VAR('x')
y = VAR('y')
z = VAR('z')


@for_each([
    (I, []),
    (x, [x]),
    (APP(I, x), [x]),
    (APP(x, x), [x]),
    (APP(x, y), [x, y]),
    (APP(x, APP(APP(J, y), APP(K, z))), [x, y, z]),
    (QUOTE(x), [x]),
    (APP(x, QUOTE(y)), [x, y]),
])
def test_free_vars(code, free):
    assert free_vars(code) == frozenset(free)


@for_each([
    (I, 1),
    (K, 1),
    (x, 2),
    (APP(K, I), 3),
    (APP(I, x), 4),
    (QUOTE(I), 2),
    (FUN(x, I), 4),
    (LET(x, I, x), 6),
    (APP(APP(S, I), I), 5),
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
    {'code': J, 'polish': 'J', 'sexpr': 'J'},
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
    {'code': x, 'polish': 'VAR x', 'sexpr': '(VAR x)'},
    {'code': APP(K, I), 'polish': 'APP K I', 'sexpr': '(K I)'},
    {
        'code': QUOTE(APP(I, K)),
        'polish': 'QUOTE APP I K',
        'sexpr': '(QUOTE (I K))',
    },
    {
        'code': FUN(x, APP(x, x)),
        'polish': 'FUN VAR x APP VAR x VAR x',
        'sexpr': '(FUN (VAR x) (VAR x (VAR x)))',
    },
    {
        'code': LET(x, I, APP(I, I)),
        'polish': 'LET VAR x I APP I I',
        'sexpr': '(LET (VAR x) I (I I))',
    },
]


@for_each(EXAMPLES)
def test_polish_parse(example):
    actual = polish_print(example['code'])
    assert actual == example['polish']


@for_each(EXAMPLES)
def test_polish_print(example):
    actual = polish_parse(example['polish'])
    assert actual == example['code']


@for_each(EXAMPLES)
def test_sexpr_parse(example):
    actual = sexpr_print(example['code'])
    assert actual == example['sexpr']


@for_each(EXAMPLES)
def test_sexpr_print(example):
    actual = sexpr_parse(example['sexpr'])
    assert actual == example['code']


# ----------------------------------------------------------------------------
# Property-based tests

alphabet = '_abcdefghijklmnopqrstuvwxyz'
s_vars = s.builds(
    VAR,
    s.builds(str, s.text(alphabet=alphabet, min_size=1, average_size=5)),
)
s_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
    s.just(J),
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
    ),
)


def s_terms_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(QUOTE, terms),
        s.builds(FUN, s_vars, terms),
        s.builds(LET, s_vars, terms, terms),
    )


s_terms = s.recursive(s_atoms, s_terms_extend, max_leaves=100)
s_sexprs = s.builds(to_sexpr, s_terms)


@hypothesis.given(s_terms)
def test_free_vars_runs(code):
    free_vars(code)


@hypothesis.given(s_terms)
def test_complexity_runs(code):
    complexity(code)


@hypothesis.given(s_terms)
@hypothesis.settings(max_examples=1000)
def test_polish_print_parse(code):
    string = polish_print(code)
    assert isinstance(string, str)
    actual_code = polish_parse(string)
    assert actual_code == code


@hypothesis.given(s_terms)
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


@hypothesis.given(s_terms)
@hypothesis.settings(max_examples=1000)
def test_sexpr_print_parse(code):
    string = sexpr_print(code)
    assert isinstance(string, str)
    actual_code = sexpr_parse(string)
    assert actual_code == code
