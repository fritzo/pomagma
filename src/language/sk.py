import simplejson as json
from math import log

binary_probs = {
    'APP'   : 0.374992,
    'COMP'  : 0.198589,
}

nullary_weights = {
    'B'     : 1.0,
    'C'     : 1.30428,
    #'C B'   : 1.35451,
    #'C I'   : 1.74145,
    'I'     : 2.21841,
    'Y'     : 2.2918,
    'K'     : 2.6654,
    'S'     : 2.69459,
    #'S B'   : 3.5036,
    #'F'     : 3.72682,
    #'S I'   : 4.12483,
    'W'     : 4.36313,
    #'W B'   : 4.3719,
    #'W I'   : 6.21147,
}

nullary_prob = 1.0 - sum(binary_probs.values())
nullary_probs = { key: -log(val) for key, val in nullary_weights.iteritems() }
scale = nullary_prob / sum(nullary_probs.values())
for key in nullary_probs.keys():
    nullary_probs[key] *= scale

probs = {
    'Nullary': nullary_probs,
    'Binary': binary_probs,
}


def make(outfile='sk.json'):
    with open(outfile, 'w') as f:
        json.dump(probs, f, indent=4)


if __name__ == '__main__':
    make()
