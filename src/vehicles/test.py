import os
import glob
import simplejson as json
from nose.tools import assert_list_equal, assert_almost_equal
from pomagma.vehicles import dict_to_vehicle, vehicle_to_dict, normalize_dict


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))


def assert_converts(expected):
    vehicle = dict_to_vehicle(expected)
    actual = vehicle_to_dict(vehicle)
    assert_list_equal(expected.keys(), actual.keys())
    for arity in expected.keys():
        assert_list_equal(expected[arity].keys(), actual[arity].keys())
        for term, weight in expected[arity].iteritems():
            assert_almost_equal(weight, actual[arity][term])


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
        with open(filename) as f:
            example = json.load(f)
        normalize_dict(example)
        yield assert_converts, example
