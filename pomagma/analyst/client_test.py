import json
import os

import pytest

import pomagma.analyst
import pomagma.cartographer
import pomagma.surveyor
import pomagma.util
from pomagma.atlas.bootstrap import THEORY, WORLD
from pomagma.util import TRAVIS_CI, unicode_to_str
from pomagma.util.testing import for_each


# Python 3 compatibility: define cmp function that was removed
def cmp(a, b):
    return (a > b) - (a < b)


DATA = os.path.join(pomagma.util.DATA, "test", "debug", "atlas", THEORY)
ADDRESS = "ipc://{}".format(os.path.join(DATA, "analyst.socket"))
OPTIONS = {
    "log_file": os.path.join(DATA, "analyst_test.log"),
    "log_level": pomagma.util.LOG_LEVEL_DEBUG,
}


def json_load(filename):
    filename = os.path.join(os.path.dirname(__file__), filename)
    with open(filename) as f:
        obj = json.load(f)
    return unicode_to_str(obj)


SIMPLIFY_EXAMPLES = json_load("testdata/simplify_examples.json")
SIMPLIFY_EXAMPLES += json_load("testdata/simplify_sugar_examples.json")
VALIDATE_EXAMPLES = json_load("testdata/validate_examples.json")
CORPUS = json_load("testdata/corpus.json")


def setup_module():
    if not os.path.exists(WORLD):
        print("Building test fixture"), WORLD
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
    print("starting server")
    server = serve()
    try:
        print("connecting client")
        with server.connect() as client:
            for _ in range(10):
                print("pinging server")
                client.ping()
    finally:
        print("stopping server")
        server.stop()


def test_ping_id():
    expected = "test"
    with load() as db:
        actual = db.ping_id(expected)
    assert actual == expected


def test_inference():
    with load() as db:
        print("Testing analyst inference")
        fail_count = db.test_inference()
    assert fail_count == 0, f"analyst failed with {fail_count} errors"


def assert_equal_example(expected, actual, example, cmp=cmp):
    assert not cmp(expected, actual), "\n".join(
        [
            f"failed {example}",
            f"expected: {expected}",
            f"actual: {actual}",
        ]
    )


def assert_examples(examples, expected, actual, cmp=cmp):
    assert len(expected) == len(examples)
    assert len(actual) == len(examples)
    for example, e, a in zip(examples, expected, actual):
        print(f"{example} : {e}")
        if cmp(e, a):
            print(f"WARNING {example}\n  expected: {e}\n  actual: {a}")
    for example, e, a in zip(examples, expected, actual):
        assert_equal_example(e, a, example, cmp)


def cmp_trool(x, y):
    if x is None or y is None:
        return 0
    return cmp(x, y)


def cmp_validity(x, y):
    return cmp_trool(x["is_top"], y["is_top"]) or cmp_trool(x["is_bot"], y["is_bot"])


def transpose(lists):
    return [list(x) for x in zip(*lists)]


def test_simplify():
    codes, expected = transpose(SIMPLIFY_EXAMPLES)
    with load() as db:
        actual = db.simplify(codes)
    assert_examples(codes, expected, actual)


SOLVE_EXAMPLES = [
    {
        "var": "x",
        "theory": "LESS x I   LESS I x",
        "necessary": ["I"],
    },
    {
        "var": "x",
        "theory": "LESS x I   LESS I x",
        "max_solutions": 999,
        "necessary": ["I"],
    },
    {
        "var": "x",
        "theory": "LESS TOP x",
        "necessary": ["TOP"],
    },
    {
        "var": "x",
        "theory": "FIXES TOP x",
        "necessary": ["TOP"],
    },
    {
        "var": "x",
        "theory": "EQUAL APP x x x",
        "max_solutions": 4,
        "necessary": ["I", "BOT", "TOP", "V"],
    },
    {
        "var": "x",
        "theory": "EQUAL APP x x x   NLESS x BOT",
        "max_solutions": 3,
        "necessary": ["I", "TOP", "V"],
    },
    {
        "var": "x",
        "theory": "EQUAL APP x TOP APP x BOT   NLESS APP K APP x I x",
        "necessary": [],
    },
    {
        "var": "s",
        "theory": "LESS APP V s s",
        "necessary": ["I", "TOP", "V", "APP CB TOP", "APP V C"],
        "possible": [],
    },
    {
        "var": "s",
        "theory": "LESS APP s BOT BOT",
        "necessary": ["B", "C", "I", "BOT", "Y"],
        "possible": [],
    },
    {
        "var": "s",
        "theory": "EQUAL APP s I I",
        "necessary": ["B", "CB", "I", "V", "COMP B B"],
        "possible": [],
    },
    {
        "var": "s",
        "theory": "LESS TOP APP s TOP",
        "necessary": ["B", "C", "I", "Y", "TOP"],
        "possible": [],
    },
    {
        "var": "s",
        "theory": """
            NLESS x BOT
            --------------
            LESS I APP s x
            """,
        "necessary": [],
        "possible": ["TOP", "J", "V", "P", "APP C K"],
    },
    {  # FIXME
        "skip_compare": "spuriously fails with either JOIN B CB or JOIN CB B",
        "var": "s",
        "theory": """
            NLESS x I
            ----------------
            LESS TOP APP s x
            """,
        "necessary": [],
        "possible": [
            "TOP",
            "JOIN B CB",
            "APP C Y",
            "JOIN CI B",
            "RAND CI B",
        ],
    },
    {  # FIXME
        "skip_compare": "spuriously fails with either RAND B CI or RAND CI B",
        "var": "s",
        "theory": """
            # The entire theory of SEMI:
            LESS APP V s s       NLESS x BOT      NLESS x I
            LESS APP s BOT BOT   --------------   ----------------
            EQUAL APP s I I      LESS I APP s x   LESS TOP APP s x
            LESS TOP APP s TOP
            """,
        "necessary": [],
        "possible": [
            "APP C Y",
            "RAND CI B",
            "JOIN CI CB",
            "RAND CI CB",
            "RAND C CI",
        ],
    },
    {
        "skip": "compiler fails",  # FIXME
        "var": "x",
        "theory": "EQUAL x I",
        "necessary": ["I"],
    },
    {
        "skip": "compiler fails",  # FIXME
        "var": "x",
        "theory": "NLESS x x",
        "necessary": [],
        "possible": [],
    },
]


@for_each(SOLVE_EXAMPLES)
def test_solve(example):
    if "skip" in example:
        pytest.xfail(example["skip"])
    with load() as db:
        max_solutions = example.get("max_solutions", 5)
        actual = db.solve(example["var"], example["theory"], max_solutions)
        if "skip_compare" in example:
            pytest.xfail(example["skip_compare"])
        for key in ["necessary", "possible"]:
            if key in example:
                assert_equal_example(example[key], actual[key], (example, key))


def test_validate():
    expected, codes = transpose(VALIDATE_EXAMPLES)
    with load() as db:
        actual = db.validate(codes)
    assert_examples(codes, expected, actual, cmp_validity)


def validate_corpus(lines, max_attempts=100):
    with load() as db:
        for attempt in range(1, 1 + max_attempts):
            print("validating corpus, attempt", attempt)
            results = db.validate_corpus(lines)
            if not any(result["pending"] for result in results):
                for validity in results:
                    del validity["pending"]
                return results
    raise ValueError(f"validate_corpus did not complete in {max_attempts} attempts")


def test_validate_corpus():
    expected, lines = transpose(CORPUS)
    actual = validate_corpus(lines)
    assert_examples(lines, expected, actual, cmp_validity)


# Some cases should be False but validate_facts is too weak to prove so.
FALSE_SKIP = True

VALIDATE_FACTS_EXAMPLES = [
    (["EQUAL APP x I I", "EQUAL APP x BOT TOP"], FALSE_SKIP),
    (["EQUAL APP x I I", "EQUAL APP x TOP BOT"], FALSE_SKIP),
    (["EQUAL BOT APP BOT BOT"], True),
    (["EQUAL BOT BOT"], True),
    (["EQUAL I I"], True),
    (["EQUAL TOP APP TOP TOP"], True),
    (["EQUAL TOP TOP"], True),
    (["EQUAL x TOP", "LESS BOT x"], True),
    (["EQUAL x TOP", "LESS TOP x"], True),
    (["EQUAL x TOP", "LESS x BOT"], False),
    (["EQUAL x x"], True),
    (["LESS APP BOT BOT BOT"], True),
    (["LESS APP I I I"], True),
    (["LESS APP K I x", "LESS APP x BOT y", "LESS I y"], True),
    (["LESS APP K I x", "LESS APP x BOT y", "NLESS I y"], False),
    (["LESS APP K I x", "NLESS I APP x I"], False),
    (["LESS APP TOP TOP TOP"], True),
    (["LESS BOT APP BOT BOT"], True),
    (["LESS BOT BOT"], True),
    (["LESS BOT I"], True),
    (["LESS BOT TOP"], True),
    (["LESS I COMP I I"], True),
    (["LESS I I"], True),
    (["LESS I JOIN I I"], True),
    (["LESS I TOP"], True),
    (["LESS I x", "LESS APP x x BOT"], False),
    (["LESS I x", "LESS APP x x y", "LESS I COMP y y"], True),
    (["LESS I x", "LESS APP x x y", "NLESS I COMP y y"], False),
    (["LESS I x", "LESS COMP x x BOT"], False),
    (["LESS I x", "LESS I APP x x"], True),
    (["LESS I x", "LESS I COMP x x"], True),
    (["LESS I x", "LESS I JOIN x x"], True),
    (["LESS I x", "LESS JOIN x x BOT"], False),
    (["LESS I x", "NLESS y I", "LESS APP x y z", "LESS z I"], FALSE_SKIP),
    (["LESS I x", "NLESS y I", "LESS APP x y z", "NLESS z I"], True),
    (["LESS K x", "LESS APP K I x", "NLESS J x"], FALSE_SKIP),
    (["LESS TOP APP TOP TOP"], True),
    (["LESS TOP BOT"], False),
    (["LESS TOP TOP"], True),
    (["LESS TOP w", "LESS w x", "LESS x y", "LESS y z", "LESS z BOT"], False),
    (["LESS TOP x", "LESS x BOT"], False),
    (["LESS TOP x", "LESS x y", "LESS y BOT"], False),
    (["LESS TOP x", "LESS x y", "LESS y z", "LESS z BOT"], False),
    (["LESS x y", "LESS y z", "NLESS z x"], FALSE_SKIP),
    (["LESS x y", "NLESS y x"], FALSE_SKIP),
    (["LESS y I", "LESS I x", "LESS x y"], True),
    (["LESS y I", "LESS I x", "LESS y x"], True),
    (["LESS y I", "LESS I x", "NLESS x y"], True),
    (["LESS y I", "LESS I x", "NLESS y x"], False),
    (["NLESS APP BOT BOT BOT"], False),
    (["NLESS APP I I I"], False),
    (["NLESS APP TOP TOP TOP"], False),
    (["NLESS BOT APP BOT BOT"], False),
    (["NLESS BOT BOT"], False),
    (["NLESS I APP I I"], False),
    (["NLESS I BOT"], True),
    (["NLESS I I"], False),
    (["NLESS TOP APP TOP TOP"], False),
    (["NLESS TOP BOT"], True),
    (["NLESS TOP I"], True),
    (["NLESS TOP TOP"], False),
    (["NLESS x x"], FALSE_SKIP),
    ([], True),
]


def test_validate_facts():
    if TRAVIS_CI:
        pytest.skip("this test is flaky on travis")
    with load() as db:
        facts, expected = transpose(VALIDATE_FACTS_EXAMPLES)
        actual = [db.validate_facts(f) for f in facts]
        assert_examples(facts, expected, actual, cmp_trool)


def test_get_histogram():
    lines = [line for _, line in CORPUS]
    with load() as db:
        for _ in range(10):
            db.validate_corpus(lines)
        histogram = db.get_histogram()
    print("histogram:", histogram)
    assert histogram["obs"]
    assert histogram["symbols"]


def validate_language(language):
    total = sum(language.values())
    assert abs(total - 1) < 1e-4, f"bad total: {total}"
    assert isinstance(language, dict), language
    for key, val in list(language.items()):
        assert isinstance(key, str), key
        assert isinstance(val, float), val
        assert val > 0, f"{key} has no mass"


def test_fit_language_histogram():
    with load() as db:
        lines = [line for _, line in CORPUS]
        for _ in range(10):
            db.validate_corpus(lines)
        histogram = db.get_histogram()
        language = db.fit_language(histogram)
        validate_language(language)


def test_fit_language_default():
    with load() as db:
        lines = [line for _, line in CORPUS]
        for _ in range(10):
            db.validate_corpus(lines)
        language = db.fit_language()
        validate_language(language)
