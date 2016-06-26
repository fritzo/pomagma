from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import VAR, APP, JOIN, FUN, LET
from pomagma.reducer.code import free_vars
from pomagma.reducer.code import polish_parse, polish_print
from pomagma.reducer.code import sexpr_parse, sexpr_print
from pomagma.reducer.code import sexpr_parse_sexpr, sexpr_print_sexpr
from pomagma.reducer.code import to_sexpr, from_sexpr
from pomagma.util.testing import for_each
import hypothesis
import hypothesis.strategies as s

x = VAR('x')
y = VAR('y')
z = VAR('z')

EXAMPLES = [
    ('HOLE', HOLE),
    ('TOP', TOP),
    ('BOT', BOT),
    ('I', I),
    ('K', K),
    ('B', B),
    ('C', C),
    ('S', S),
    ('VAR x', x),
    ('APP I K', APP(I, K)),
    ('JOIN K APP K I', JOIN(K, APP(K, I))),
    ('APP APP I K JOIN B C', APP(APP(I, K), JOIN(B, C))),
    ('FUN VAR x APP VAR x VAR x', FUN(x, APP(x, x))),
    ('LET VAR x I APP I I', LET(x, I, APP(I, I))),
]


@for_each(EXAMPLES)
def test_polish_parse(string, code):
    actual_string = polish_print(code)
    assert actual_string == string


@for_each(EXAMPLES)
def test_polish_print(string, code):
    actual_code = polish_parse(string)
    assert actual_code == code


@for_each([
    (I, []),
    (x, [x]),
    (APP(I, x), [x]),
    (APP(x, x), [x]),
    (APP(x, y), [x, y]),
    (APP(x, JOIN(y, APP(K, z))), [x, y, z]),
])
def test_free_vars(code, free):
    assert free_vars(code) == set(free)


alphabet = '_abcdefghijklmnopqrstuvwxyz'
s_vars = s.builds(
    VAR,
    s.builds(str, s.text(alphabet=alphabet, min_size=1, average_size=5)),
)
s_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(HOLE),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
)


def s_terms_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(JOIN, terms, terms),
        s.builds(FUN, s_vars, terms),
        s.builds(LET, s_vars, terms, terms),
    )


s_terms = s.recursive(s_atoms, s_terms_extend, max_leaves=100)
s_sexprs = s.builds(to_sexpr, s_terms)


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
