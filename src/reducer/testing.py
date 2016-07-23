from pomagma.reducer.code import EQUAL, is_app, is_quote, sexpr_parse
from pomagma.reducer.linker import link
import os
import pytest

DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(DIR, 'testdata')


def iter_test_cases(suites, test_id=None):
    print('test_id = {}'.format(test_id))
    for suite in suites:
        filename = '{}/{}.sexpr'.format(TESTDATA, suite)
        print('reading {}'.format(filename))
        with open(filename) as f:
            for i, line in enumerate(f):
                parts = line.split('#', 1)
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
