import re
from nose.tools import assert_set_equal
from pomagma.util.testing import for_each_kwargs
from pomagma.analyst.compiler import compile_solver


EXAMPLES = [
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


def parse_programs(script):
    script = re.sub('#.*\n', '', script)
    scripts = re.split('\n\n', script)
    return set(tuple(s.strip().split('\n')) for s in scripts)


@for_each_kwargs(EXAMPLES)
def test_compile_solver(result, constraints, expected_programs):
    script = compile_solver(result, constraints)
    actual_programs = parse_programs(script)
    assert_set_equal(expected_programs, actual_programs)
