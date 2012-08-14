from pomagma import run

def test_contrapositive():
    run.contrapositves(
            'sk.rules',
            'join.rules',
            'rand.rules',
            'quote.rules',
            )

def test_sk():
    run.measure('sk.rules')

def test_join():
    run.measure('join.rules')

def test_rand():
    run.measure('rand.rules')

def test_quote():
    run.measure('quote.rules')
