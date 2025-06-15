import itertools

from pomagma.compiler.util import eval_float44, eval_float53


def test_eval_float44():
    values = list(map(eval_float44, list(range(256))))
    print(" ".join([f"{k}:{v}" for k, v in enumerate(values)]))
    for i, j in itertools.pairwise(values):
        assert i < j
        assert j - i - 1 < 0.08 * j  # less than 8% wasted space


def test_eval_float53():
    values = list(map(eval_float53, list(range(256))))
    print(" ".join([f"{k}:{v}" for k, v in enumerate(values)]))
    for i, j in itertools.pairwise(values):
        assert i < j
        assert j - i - 1 < 0.04 * j  # less than 4% wasted space
