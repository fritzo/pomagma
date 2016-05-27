from .util import dict_to_language
from .util import json_load
from .util import language_to_dict
from .util import normalize_dict
import glob
import os

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))


def assert_converts(expected):
    language = dict_to_language(expected)
    actual = language_to_dict(language)
    assert set(expected.keys()) == set(actual.keys())
    for arity in expected.keys():
        assert set(expected[arity].keys()) == set(actual[arity].keys())
        for term, weight in expected[arity].iteritems():
            assert abs(weight - actual[arity][term]) < 1e-8


def test_example():
    example = {
        'NULLARY': {
            'B': 1.0,
            'C': 1.30428,
            'I': 2.21841,
            'K': 2.6654,
            'S': 2.69459,
        },
        'BINARY': {
            'APP': 0.4,
            'COMP': 0.2,
        },
    }
    normalize_dict(example)
    assert_converts(example)


def test_convert_json():
    for filename in glob.glob(os.path.join(SCRIPT_DIR, '*.json')):
        example = json_load(filename)
        normalize_dict(example)
        yield assert_converts, example
