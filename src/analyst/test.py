import os
from itertools import izip
import pomagma.util
import pomagma.surveyor
import pomagma.cartographer
import pomagma.analyst

THEORY = os.environ.get('THEORY', 'skj')
DATA = os.path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', THEORY)
WORLD = os.environ.get('WORLD', os.path.join(DATA, '0.normal.h5'))
ADDRESS = 'ipc://{}'.format(os.path.join(DATA, 'socket'))
OPTIONS = {
    'log_file': os.path.join(DATA, 'analyst_test.log'),
    'log_level': pomagma.util.LOG_LEVEL_DEBUG,
}


def setup_module():
    if not os.path.exists(WORLD):
        print 'Building test fixture', WORLD
        min_size = pomagma.util.MIN_SIZES[THEORY]
        pomagma.surveyor.init(THEORY, WORLD, min_size)
        with pomagma.cartographer.load(THEORY, WORLD) as db:
            db.normalize()
            db.dump(WORLD)


def serve(address=ADDRESS):
    setup_module()
    return pomagma.analyst.serve(THEORY, WORLD, address, **OPTIONS)


def test_ping():
    print 'starting server'
    server = serve()
    try:
        print 'connecting client'
        client = server.connect()
        for _ in xrange(10):
            print 'pinging server'
            client.ping()
    finally:
        print 'stoping server'
        server.stop()


def test_inference():
    with pomagma.analyst.load(THEORY, WORLD, **OPTIONS) as db:
        print 'Testing analyst inference'
        fail_count = db.test_inference()
    assert fail_count == 0, 'analyst failed with {} errors'.format(fail_count)


DEFINE = lambda name, code: {'name': name, 'code': code}
ASSERT = lambda code: {'name': None, 'code': code}

TOP = {'is_top': True, 'is_bot': False}
BOT = {'is_top': False, 'is_bot': True}
OK = {'is_top': False, 'is_bot': False}


def assert_examples(examples, expected, actual, cmp=cmp):
    assert len(expected) == len(examples)
    assert len(actual) == len(examples)
    for example, e, a in izip(examples, expected, actual):
        if e != a:
            print 'WARNING {}\n  expected: {}\n  actual: {}'.format(
                example, e, a)
    for example, e, a in izip(examples, expected, actual):
        assert not cmp(e, a),\
            'failed {}\n  expected: {}\n  actual: {}'.format(example, e, a)


def cmp_trool(x, y):
    if x is None or y is None:
        return 0
    else:
        return cmp(x, y)


def cmp_validity(x, y):
    return (cmp_trool(x['is_top'], y['is_top']) or
            cmp_trool(x['is_bot'], y['is_bot']))


SIMPLIFY_EXAMPLES = [
    ('TOP', 'TOP'),
    ('BOT', 'BOT'),
    ('I', 'I'),
    ('APP I I', 'I'),
    ('COMP I I', 'I'),
    ('JOIN BOT TOP', 'TOP'),
]


transpose = lambda lists: map(list, izip(* lists))


def test_simplify():
    codes, expected = transpose(SIMPLIFY_EXAMPLES)
    with pomagma.analyst.load(THEORY, WORLD, **OPTIONS) as db:
        actual = db.simplify(codes)
    assert_examples(codes, expected, actual)


VALIDATE_EXAMPLES = [
    (BOT, 'BOT'),
    (TOP, 'TOP'),
    (OK, 'I'),
    (OK, 'APP I I'),
    (OK, 'COMP I I'),
]


def test_validate():
    expected, codes = transpose(VALIDATE_EXAMPLES)
    with pomagma.analyst.load(THEORY, WORLD, **OPTIONS) as db:
        actual = db.validate(codes)
    assert_examples(codes, expected, actual, cmp_validity)


CORPUS = [
    (TOP, ASSERT('TOP')),
    (BOT, ASSERT('BOT')),
    (OK, ASSERT('I')),
    (OK, DEFINE('true', 'K')),
    (OK, DEFINE('false', 'APP K I')),
    # \x,f. f x
    # = \x. C I x
    # = C I
    (OK, DEFINE('box', 'APP C I')),
    (OK, ASSERT('APP I APP VAR box I')),
    # \x,y,f. f x y
    # = \x,y. C (C I x) y
    # = \x. C (C I x)
    # = C * (C I)
    (OK, DEFINE('push', 'COMP C VAR box')),
    # recursion
    (OK, DEFINE('push_unit', 'APP C APP VAR box I')),
    (OK, ASSERT('APP VAR push_unit BOT')),
    (OK, ASSERT('APP VAR push_unit TOP')),
    (OK, DEFINE('uuu', 'APP VAR push_unit VAR uuu')),
    # mutual recursion
    (OK, DEFINE('push_true', 'APP C APP VAR box VAR true')),
    (OK, DEFINE('push_false', 'APP C APP VAR box VAR false')),
    (OK, DEFINE('tftftf', 'APP VAR push_true VAR ftftft')),
    (OK, DEFINE('ftftft', 'APP VAR push_false VAR tftftf')),
]


def validate_corpus(lines, max_attempts=100):
    with pomagma.analyst.load(THEORY, WORLD, **OPTIONS) as db:
        for attempt in xrange(1, 1 + max_attempts):
            print 'validating corpus, attempt', attempt
            results = db.validate_corpus(lines)
            if not any(result['pending'] for result in results):
                for validity in results:
                    del validity['pending']
                return results
    raise ValueError(
        'validate_corpus did not complete in {} attempts'.format(max_attempts))


def test_validate_corpus():
    expected, lines = transpose(CORPUS)
    actual = validate_corpus(lines)
    assert_examples(lines, expected, actual, cmp_validity)
