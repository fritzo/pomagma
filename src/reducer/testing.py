"""Tools for testing implementations of reduce() and simplify()."""

from pomagma.reducer.code import CODE, EVAL, QQUOTE, QAPP, EQUAL, LESS
from pomagma.reducer.code import is_app, is_quote, sexpr_parse
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import UNIT, BOOL, MAYBE
from pomagma.reducer.code import VAR, APP, QUOTE
from pomagma.reducer.linker import link
import hypothesis.strategies as s
import os
import pytest

DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(DIR, 'testdata')


# ----------------------------------------------------------------------------
# parameterized testing

def iter_test_cases(suites, test_id=None):
    print('test_id = {}'.format(test_id))
    for suite in suites:
        filename = '{}/{}.sexpr'.format(TESTDATA, suite)
        print('reading {}'.format(filename))
        with open(filename) as f:
            for i, line in enumerate(f):
                parts = line.split(';', 1)
                sexpr = parts[0].strip()
                if sexpr:
                    code = sexpr_parse(sexpr)
                    comment = None if len(parts) < 2 else parts[1].strip()
                    message = 'In {}:{}\n{}'.format(filename, 1 + i, line)
                    yield code, comment, message


def parse_xfail(comment, test_id):
    if comment.startswith('xfail'):
        if test_id is None:
            return True
        if test_id in comment[len('xfail'):].strip().split(', '):
            return True
    return False


def iter_equations(suites, test_id=None):
    for code, comment, message in iter_test_cases(suites, test_id=test_id):
        if is_app(code) and is_app(code[1]) and code[1][1] is EQUAL:
            lhs = code[1][2]
            rhs = code[2]
            if is_quote(lhs) and is_quote(rhs):
                lhs = link(lhs[1], lazy=False)
                rhs = link(rhs[1], lazy=False)
                example = lhs, rhs, message
                if comment and parse_xfail(comment, test_id):
                    example = pytest.mark.xfail(example)
                yield example


# ----------------------------------------------------------------------------
# property-based testing

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
        s.just(UNIT),
        s.just(BOOL),
        s.just(MAYBE),
    ),
)


def s_codes_extend(codes):
    return s.one_of(
        s.builds(APP, codes, codes),
        s.builds(QUOTE, codes),
    )


s_codes = s.recursive(s_atoms, s_codes_extend, max_leaves=100)
s_quoted = s.builds(QUOTE, s_codes)
