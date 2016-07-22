from pomagma.reducer.code import EQUAL, is_app, is_quote, sexpr_parse
import os

DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(DIR, 'testdata')


def iter_test_cases(stem):
    filename = '{}/{}.sexpr'.format(TESTDATA, stem)
    print('reading {}'.format(filename))
    with open(filename) as f:
        for line in f:
            line = line.split('#', 1)[0].strip()
            if line:
                yield sexpr_parse(line)


def iter_equations(stem):
    for code in iter_test_cases(stem):
        if is_app(code) and is_app(code[1]) and code[1][1] is EQUAL:
            lhs = code[1][2]
            rhs = code[2]
            if is_quote(lhs) and is_quote(rhs):
                yield lhs[1], rhs[1]
