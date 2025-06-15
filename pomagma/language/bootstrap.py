import os
from math import exp

from parsable import parsable

import pomagma.util

from . import util

SPECS = {}

SPECS["sk"] = {
    "binary_probs": {
        "APP": 0.374992,
        "COMP": 0.198589,
    },
    "nullary_weights": {
        "B": 1.0,
        "C": 1.30428,
        "CB": 1.35451,
        "CI": 1.74145,
        "I": 2.21841,
        "Y": 2.2918,
        "K": 2.6654,
        "S": 2.69459,
        # 'S B': 3.5036,
        # 'F': 3.72682,
        # 'S I': 4.12483,
        "W": 4.36313,
        # 'W B': 4.3719,
        # 'W I': 6.21147,
    },
}

SPECS["skj"] = {
    "binary_probs": {
        "APP": 0.374992,
        "COMP": 0.198589,
    },
    "symmetric_probs": {
        "JOIN": 0.0569286,
    },
    "nullary_weights": {
        "B": 1.0,
        "C": 1.30428,
        "CB": 1.35451,
        "CI": 1.74145,
        "I": 2.21841,
        "Y": 2.2918,
        "K": 2.6654,
        "S": 2.69459,
        "J": 2.81965,
        "V": 2.87327,
        "BOT": 3.0,
        "TOP": 3.0,
        # 'S B': 3.5036,
        "P": 3.69204,
        "F": 3.72682,
        # 'S I': 4.12483,
        "W": 4.36313,
        # 'W B': 4.3719,
        # 'W I': 6.21147,
        "U": 6.3754,
    },
}

SPECS["skja"] = {
    "binary_probs": {
        "APP": 0.374992,
        "COMP": 0.198589,
    },
    "symmetric_probs": {
        "JOIN": 0.0569286,
    },
    "nullary_weights": {
        "B": 1.0,
        "C": 1.30428,
        "CB": 1.35451,
        "CI": 1.74145,
        "I": 2.21841,
        "Y": 2.2918,
        "K": 2.6654,
        "S": 2.69459,
        "J": 2.81965,
        "V": 2.87327,
        "BOT": 3.0,
        "TOP": 3.0,
        "DIV": 3.06752,
        # 'S B': 3.5036,
        "P": 3.69204,
        "F": 3.72682,
        # 'S I': 4.12483,
        "SEMI": 4.18665,
        "W": 4.36313,
        "UNIT": 4.3634,
        # 'W B': 4.3719,
        "A": 5.0,
        # 'SECTION': 5.0,
        # 'RETRACT': 5.0,
        "BOOL": 5.21614,
        # 'W I': 6.21147,
        "U": 6.3754,
        "BOOOL": 7.0,
        # 'PROD': 12.0,
        # 'SUM': 12.0,
        # 'MAYBE': 12.0,
        # 'SSET': 12.0,
    },
}

SPECS["skrj"] = {
    "binary_probs": {
        "APP": 0.34,
        "COMP": 0.18,
    },
    "symmetric_probs": {
        "JOIN": 0.05,
        "RAND": 0.05,
    },
    "nullary_weights": {
        "B": 1.0,
        "C": 1.30428,
        "CB": 1.35451,
        "CI": 1.74145,
        "I": 2.21841,
        "Y": 2.2918,
        "K": 2.6654,
        "S": 2.69459,
        "J": 2.81965,
        "R": 2.81965,
        "V": 2.87327,
        "BOT": 3.0,
        "TOP": 3.0,
        # 'DIV': 3.06752,
        # 'S B': 3.5036,
        "P": 3.69204,
        "F": 3.72682,
        # 'S I': 4.12483,
        # 'SEMI': 4.18665,
        "W": 4.36313,
        # 'UNIT': 4.3634,
        # 'W B': 4.3719,
        # 'A': 5.0,
        # 'SECTION': 5.0,
        # 'RETRACT': 5.0,
        # 'BOOL': 5.21614,
        # 'W I': 6.21147,
        "U": 6.3754,
        # 'PROD': 12.0,
        # 'SUM': 12.0,
        # 'MAYBE': 12.0,
        # 'SSET': 12.0,
    },
}


@parsable
def make(theory):
    """Bootstrap a language from Johann.

    Inputs: theory in ['sk', 'skj', 'skja', 'skrj']

    """
    spec = SPECS[theory]
    nullary_weights = spec.get("nullary_weights", {})
    injective_probs = spec.get("injective_probs", {})
    binary_probs = spec.get("binary_probs", {})
    symmetric_probs = spec.get("symmetric_probs", {})

    compound_prob = (
        sum(injective_probs.values())
        + sum(binary_probs.values())
        + sum(symmetric_probs.values())
    )
    assert compound_prob < 1
    nullary_prob = 1.0 - compound_prob
    nullary_probs = {key: exp(-val) for key, val in list(nullary_weights.items())}
    scale = nullary_prob / sum(nullary_probs.values())
    for key in list(nullary_probs.keys()):
        nullary_probs[key] *= scale

    probs = {
        "NULLARY": nullary_probs,
        "INJECTIVE": injective_probs,
        "BINARY": binary_probs,
        "SYMMETRIC": symmetric_probs,
    }
    for arity, group in list(probs.items()):
        if not group:
            del probs[arity]

    with pomagma.util.chdir(os.path.dirname(os.path.abspath(__file__))):
        util.json_dump(probs, f"{theory}.json")
        # util.compile('{}.json'.format(theory), '{}.language'.format(theory))


if __name__ == "__main__":
    parsable()
