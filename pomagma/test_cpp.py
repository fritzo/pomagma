from pomagma import run

def test_cpp():
    run.compile(
            'sk.rules',
            'join.rules',
            'rand.rules',
            'quote.rules',
            )
