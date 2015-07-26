import re
from nose.tools import assert_set_equal
from pomagma.analyst.compiler import compile_cosolver
from pomagma.analyst.compiler import compile_solver
from pomagma.compiler.util import union
from pomagma.util.testing import for_each_kwargs


def parse_programs(script):
    script = re.sub('#.*\n', '', script)
    scripts = re.split('\n\n', script)
    return set(tuple(s.strip().splitlines()) for s in scripts)


SOLVE_EXAMPLES = [
    {
        'result': 'x',
        'constraints': [],
        'expected_programs': set([
            ('LETS_UNARY_RELATION RETURN RETURN_x',
             'FOR_NEG x RETURN_x',
             'INFER_UNARY_RELATION RETURN x'),
        ]),
    },
    {
        'result': 'x',
        'constraints': ['LESS x I'],
        'expected_programs': set([
            ('FOR_NULLARY_FUNCTION I I_',
             'LETS_BINARY_RELATION_RHS LESS LESS_x_I I_',
             'LETS_UNARY_RELATION RETURN RETURN_x',
             'FOR_POS_NEG x LESS_x_I RETURN_x',
             'INFER_UNARY_RELATION RETURN x'),
            ('FOR_NULLARY_FUNCTION I I_',
             'LETS_BINARY_RELATION_RHS NLESS NLESS_x_I I_',
             'LETS_UNARY_RELATION NRETURN NRETURN_x',
             'FOR_POS_NEG x NLESS_x_I NRETURN_x',
             'INFER_UNARY_RELATION NRETURN x'),
        ]),
    },
]


@for_each_kwargs(SOLVE_EXAMPLES)
def test_compile_solver(result, constraints, expected_programs):
    script = compile_solver(result, constraints)
    actual_programs = parse_programs(script)
    assert_set_equal(expected_programs, actual_programs)


COSOLVE_EXAMPLES = [
    {
        'var': 's',
        'theory': 'LESS APP V s s',
        'expected_programs': set([
            ('FOR_NULLARY_FUNCTION V V_',
             'LETS_BINARY_FUNCTION_LHS APP V_ APP_V_s',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_POS_NEG s APP_V_s NRETURN_s',
             'LET_BINARY_FUNCTION APP V_ s APP_V_s',
             'IF_BINARY_RELATION NLESS APP_V_s s',
             'INFER_UNARY_RELATION NRETURN s'),
        ]),
    },
    {
        'var': 's',
        'theory': 'LESS APP s BOT BOT',
        'expected_programs': set([
            ('FOR_NULLARY_FUNCTION BOT BOT_',
             'LETS_BINARY_FUNCTION_RHS APP APP_s_BOT BOT_',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_POS_NEG s APP_s_BOT NRETURN_s',
             'LET_BINARY_FUNCTION APP s BOT_ APP_s_BOT',
             'IF_BINARY_RELATION NLESS APP_s_BOT BOT_',
             'INFER_UNARY_RELATION NRETURN s'),
        ]),
    },
    {
        'var': 's',
        'theory': 'EQUAL APP s I I',
        'expected_programs': set([
            ('FOR_NULLARY_FUNCTION I I_',
             'LETS_BINARY_FUNCTION_RHS APP APP_s_I I_',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_POS_NEG s APP_s_I NRETURN_s',
             'LET_BINARY_FUNCTION APP s I_ APP_s_I',
             'IF_BINARY_RELATION NLESS APP_s_I I_',
             'INFER_UNARY_RELATION NRETURN s'),
            ('FOR_NULLARY_FUNCTION I I_',
             'LETS_BINARY_FUNCTION_RHS APP APP_s_I I_',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_POS_NEG s APP_s_I NRETURN_s',
             'LET_BINARY_FUNCTION APP s I_ APP_s_I',
             'IF_BINARY_RELATION NLESS I_ APP_s_I',
             'INFER_UNARY_RELATION NRETURN s'),

        ]),
    },
    {
        'var': 's',
        'theory': 'LESS TOP APP s TOP',
        'expected_programs': set([
            ('FOR_NULLARY_FUNCTION TOP TOP_',
             'LETS_BINARY_FUNCTION_RHS APP APP_s_TOP TOP_',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_POS_NEG s APP_s_TOP NRETURN_s',
             'LET_BINARY_FUNCTION APP s TOP_ APP_s_TOP',
             'IF_BINARY_RELATION NLESS TOP_ APP_s_TOP',
             'INFER_UNARY_RELATION NRETURN s'),

        ]),
    },
    {
        'var': 's',
        'theory': '''
            NLESS x BOT
            --------------
            LESS I APP s x
            ''',
        'expected_programs': set([
            ('FOR_BLOCK',
             'FOR_NULLARY_FUNCTION I I_',
             'FOR_NULLARY_FUNCTION BOT BOT_',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_NEG s NRETURN_s',
             'IF_BLOCK s',
             'LETS_BINARY_RELATION_RHS NLESS NLESS_x_BOT BOT_',
             'LETS_BINARY_FUNCTION_LHS APP s APP_s_x',
             'FOR_POS_POS x NLESS_x_BOT APP_s_x',
             'LET_BINARY_FUNCTION APP s x APP_s_x',
             'IF_BINARY_RELATION NLESS I_ APP_s_x',
             'INFER_UNARY_RELATION NRETURN s'),
        ]),
    },
    {
        'var': 's',
        'theory': '''
            NLESS x I
            ----------------
            LESS TOP APP s x
            ''',
        'expected_programs': set([
            ('FOR_BLOCK',
             'FOR_NULLARY_FUNCTION I I_',
             'FOR_NULLARY_FUNCTION TOP TOP_',
             'LETS_UNARY_RELATION NRETURN NRETURN_s',
             'FOR_NEG s NRETURN_s',
             'IF_BLOCK s',
             'LETS_BINARY_RELATION_RHS NLESS NLESS_x_I I_',
             'LETS_BINARY_FUNCTION_LHS APP s APP_s_x',
             'FOR_POS_POS x NLESS_x_I APP_s_x',
             'LET_BINARY_FUNCTION APP s x APP_s_x',
             'IF_BINARY_RELATION NLESS TOP_ APP_s_x',
             'INFER_UNARY_RELATION NRETURN s'),
        ]),
    },
    {
        'var': 's',
        'theory': '''
            # The entire theory of SEMI:
            LESS APP V s s       NLESS x BOT      NLESS x I
            LESS APP s BOT BOT   --------------   ----------------
            EQUAL APP s I I      LESS I APP s x   LESS TOP APP s x
            LESS TOP APP s TOP
            ''',
        'expected_programs': None,  # defined below
    },
]

COSOLVE_EXAMPLES[-1]['expected_programs'] = union(
    e['expected_programs'] for e in COSOLVE_EXAMPLES[:-1])


@for_each_kwargs(COSOLVE_EXAMPLES)
def test_compile_cosolver(var, theory, expected_programs):
    script = compile_cosolver(var, theory)
    actual_programs = parse_programs(script)
    assert_set_equal(expected_programs, actual_programs)
