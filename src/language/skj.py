import simplejson as json
from math import log

binary_probs = {
    'APP':  0.374992,
    'COMP': 0.198589,
}

symmetric_probs = {
    'JOIN': 0.0569286,
}

nullary_weights = {
    'B':    1.0,
    'C':    1.30428,
    'CB':   1.35451,
    'CI':   1.74145,
    'I':    2.21841,
    'Y':    2.2918,
    'K':    2.6654,
    'S':    2.69459,
    'J':    2.81965,
    'V':    2.87327,
    #'div':  3.06752,
    #'S B':  3.5036,
    'P':    3.69204,
    #'F':    3.72682,
    #'S I':  4.12483,
    #'semi': 4.18665,
    'W':    4.36313,
    #'unit': 4.3634,
    #'W B':  4.3719,
    #'bool': 5.21614,
    #'W I':  6.21147,
    'U':    6.3754,
    'A': 10.0,
    #'prod': 12.0,
    #'sum':  12.0,
    #'maybe': 12.0,
    #'sset': 12.0,
}

compound_prob = sum(binary_probs.values()) - sum(symmetric_probs.values())
assert compound_prob < 1
nullary_prob = 1.0 - compound_prob
nullary_probs = {key: -log(val) for key, val in nullary_weights.iteritems()}
scale = nullary_prob / sum(nullary_probs.values())
for key in nullary_probs.keys():
    nullary_probs[key] *= scale

probs = {
    'NULLARY': nullary_probs,
    'BINARY': binary_probs,
    'SYMMETRIC': symmetric_probs,
}


def make(outfile='skj.json'):
    with open(outfile, 'w') as f:
        json.dump(probs, f, indent=4)


if __name__ == '__main__':
    make()
