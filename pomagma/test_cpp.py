from pomagma import run

def test_cpp():
    run.test_compile(
            'sk.rules',
            'join.rules',
            'rand.rules',
            'quote.rules',
            )
