from pomagma.compiler import sequencer


def test_alphabet():
    assert len(sequencer.alphabet) == len(set(sequencer.alphabet))
