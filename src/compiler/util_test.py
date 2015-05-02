from nose.tools import assert_less
from pomagma.compiler.util import eval_float44
from pomagma.compiler.util import eval_float53


def test_eval_float44():
    values = map(eval_float44, range(256))
    print ' '.join(['{}:{}'.format(k, v) for k, v in enumerate(values)])
    for i, j in zip(values[:-1], values[1:]):
        assert_less(i, j)
        assert_less(j - i - 1, 0.08 * j)   # less than 8% wasted space


def test_eval_float53():
    values = map(eval_float53, range(256))
    print ' '.join(['{}:{}'.format(k, v) for k, v in enumerate(values)])
    for i, j in zip(values[:-1], values[1:]):
        assert_less(i, j)
        assert_less(j - i - 1, 0.04 * j)   # less than 4% wasted space
