import os
from itertools import izip
import pomagma.util
import pomagma.surveyor
import pomagma.cartographer
import pomagma.analyst
import simplejson as json


THEORY = os.environ.get('THEORY', 'skrj')
SIZE = pomagma.util.MIN_SIZES[THEORY]
WORLD = os.path.join(
    pomagma.util.DATA,
    'atlas',
    THEORY,
    'region.normal.{:d}.h5'.format(SIZE))
DATA = os.path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', THEORY)
ADDRESS = 'ipc://{}'.format(os.path.join(DATA, 'socket'))
OPTIONS = {
    'log_file': os.path.join(DATA, 'analyst_test.log'),
    'log_level': pomagma.util.LOG_LEVEL_DEBUG,
}


def json_load(filename):
    filename = os.path.join(os.path.dirname(__file__), filename)
    with open(filename) as f:
        return json.load(f)


SIMPLIFY_EXAMPLES = json_load('testdata/simplify_examples.json')
VALIDATE_EXAMPLES = json_load('testdata/validate_examples.json')
CORPUS = json_load('testdata/corpus.json')


def setup_module():
    if not os.path.exists(WORLD):
        print 'Building test fixture', WORLD
        dirname = os.path.dirname(WORLD)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        min_size = pomagma.util.MIN_SIZES[THEORY]
        pomagma.surveyor.init(THEORY, WORLD, min_size)
        with pomagma.cartographer.load(THEORY, WORLD) as db:
            db.normalize()
            db.dump(WORLD)


def serve(address=ADDRESS):
    setup_module()
    return pomagma.analyst.serve(THEORY, WORLD, address, **OPTIONS)


def load():
    return pomagma.analyst.load(THEORY, WORLD, **OPTIONS)


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


def test_ping_id():
    expected = 'test'
    with load() as db:
        actual = db.ping_id(expected)
    assert actual == expected


def test_inference():
    with load() as db:
        print 'Testing analyst inference'
        fail_count = db.test_inference()
    assert fail_count == 0, 'analyst failed with {} errors'.format(fail_count)


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


transpose = lambda lists: map(list, izip(* lists))


def test_simplify():
    codes, expected = transpose(SIMPLIFY_EXAMPLES)
    with load() as db:
        actual = db.simplify(codes)
    assert_examples(codes, expected, actual)


def test_validate():
    expected, codes = transpose(VALIDATE_EXAMPLES)
    with load() as db:
        actual = db.validate(codes)
    assert_examples(codes, expected, actual, cmp_validity)


def validate_corpus(lines, max_attempts=100):
    with load() as db:
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


def test_get_histogram():
    lines = [line for _, line in CORPUS]
    with load() as db:
        for _ in xrange(10):
            db.validate_corpus(lines)
        histogram = db.get_histogram()
    print 'histogram:', histogram
    assert histogram['obs']
    assert histogram['symbols']


def validate_language(language):
    total = sum(language.itervalues())
    assert abs(total - 1) < 1e-4, 'bad total: {}'.format(total)
    assert isinstance(language, dict), language
    for key, val in language.iteritems():
        assert isinstance(key, str), key
        assert isinstance(val, float), val
        assert val > 0, '{} has no mass'.format(key)


def test_fit_language_histogram():
    with load() as db:
        lines = [line for _, line in CORPUS]
        for _ in xrange(10):
            db.validate_corpus(lines)
        histogram = db.get_histogram()
        language = db.fit_language(histogram)
        validate_language(language)


def test_fit_language_default():
    with load() as db:
        lines = [line for _, line in CORPUS]
        for _ in xrange(10):
            db.validate_corpus(lines)
        language = db.fit_language()
        validate_language(language)
