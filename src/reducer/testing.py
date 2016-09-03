"""Tools for testing implementations of reduce() and simplify()."""

from importlib import import_module
from pomagma.reducer.code import CODE, EVAL, QQUOTE, QAPP, EQUAL, LESS
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import UNIT, BOOL, MAYBE
from pomagma.reducer.code import NVAR, APP, JOIN, QUOTE
from pomagma.reducer.code import is_app, is_quote, sexpr_parse
from pomagma.reducer.linker import link
from pomagma.reducer.transforms import compile_
import hypothesis.strategies as s
import os
import pytest

DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(DIR, 'testdata')


# ----------------------------------------------------------------------------
# parameterized testing

def iter_test_cases(test_id, suites=None):
    assert isinstance(test_id, str), test_id
    print('test_id = {}'.format(test_id))
    if suites is None:
        module = import_module('pomagma.reducer.{}'.format(test_id))
        suites = module.SUPPORTED_TESTDATA
    for suite in suites:
        filename = '{}/{}.sexpr'.format(TESTDATA, suite)
        print('reading {}'.format(filename))
        with open(filename) as f:
            for i, line in enumerate(f):
                parts = line.split(';', 1)
                sexpr = parts[0].strip()
                if sexpr:
                    message = 'In {}:{}\n{}'.format(filename, 1 + i, line)
                    try:
                        code = sexpr_parse(sexpr)
                    except ValueError as e:
                        raise ValueError('{} {}'.format(message, e))
                    comment = None if len(parts) < 2 else parts[1].strip()
                    yield code, comment, message


def parse_xfail(comment, test_id):
    if comment.startswith('xfail'):
        if test_id is None:
            return True
        if test_id in comment[len('xfail'):].strip().split(' '):
            return True
    return False


def iter_equations(test_id, suites=None):
    assert isinstance(test_id, str), test_id
    for code, comment, message in iter_test_cases(test_id, suites):
        if is_app(code) and is_app(code[1]) and code[1][1] is EQUAL:
            lhs = code[1][2]
            rhs = code[2]
            if is_quote(lhs) and is_quote(rhs):
                lhs = link(compile_(lhs[1]), lazy=False)
                rhs = link(compile_(rhs[1]), lazy=False)
                example = lhs, rhs, message
                if comment and parse_xfail(comment, test_id):
                    example = pytest.mark.xfail(example)
                yield example


# ----------------------------------------------------------------------------
# property-based testing

alphabet = '_abcdefghijklmnopqrstuvwxyz'
s_vars = s.builds(
    NVAR,
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
s_sk_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
)


def s_sk_extend(codes):
    return s.builds(APP, codes, codes)


def s_skj_extend(codes):
    return s.one_of(
        s.builds(APP, codes, codes),
        s.builds(JOIN, codes, codes),
    )


def s_codes_extend(codes):
    return s.one_of(
        s.builds(APP, codes, codes),
        s.builds(JOIN, codes, codes),
        s.builds(QUOTE, codes),
    )


s_sk_codes = s.recursive(s_sk_atoms, s_sk_extend, max_leaves=100)
s_skj_codes = s.recursive(s_sk_atoms, s_skj_extend, max_leaves=100)
s_codes = s.recursive(s_atoms, s_codes_extend, max_leaves=100)
s_quoted = s.builds(QUOTE, s_codes)
