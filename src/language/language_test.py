import glob
import os

from pomagma.language.util import (
    dict_to_language,
    json_load,
    language_to_dict,
    normalize_dict,
)
from pomagma.util.testing import for_each

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))


def assert_converts(expected, tol=1e-7):
    language = dict_to_language(expected)
    actual = language_to_dict(language)
    assert set(expected.keys()) == set(actual.keys())
    for arity in list(expected.keys()):
        assert set(expected[arity].keys()) == set(actual[arity].keys())
        for term, weight in list(expected[arity].items()):
            assert abs(weight - actual[arity][term]) < tol


def test_example():
    example = {
        "NULLARY": {
            "B": 1.0,
            "C": 1.30428,
            "I": 2.21841,
            "K": 2.6654,
            "S": 2.69459,
        },
        "BINARY": {
            "APP": 0.4,
            "COMP": 0.2,
        },
    }
    normalize_dict(example)
    assert_converts(example)


@for_each(glob.glob(os.path.join(SCRIPT_DIR, "*.json")))
def test_convert_json(filename):
    example = json_load(filename)
    normalize_dict(example)
    assert_converts(example)
