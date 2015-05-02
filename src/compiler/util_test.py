from nose.tools import assert_less
from pomagma.compiler.util import eval_float8


def test_eval_float8():
    values = map(eval_float8, range(256))
    print ' '.join(['{}:{}'.format(k, v) for k, v in enumerate(values)])
    for i, j in zip(values[:-1], values[1:]):
        assert_less(i, j)
        assert_less(j - i - 1, 0.05 * (j + i))   # less than 5% wasted space
