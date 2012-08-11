from pomagma import run

def test_sk():
    run.measure('sk.rules')

def test_join():
    run.measure('join.rules')

def test_rand():
    run.measure('rand.rules')

def test_quote():
    run.measure('quote.rules')
