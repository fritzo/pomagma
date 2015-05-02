from nose.tools import assert_equal
from pomagma.compiler import sequencer


def test_alphabet():
    assert_equal(len(sequencer.alphabet), len(set(sequencer.alphabet)))
