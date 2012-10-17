from pomagma.language import dict_to_language
from math import log

compound_probs = {
    'APP'   : 0.374992,
    'COMP'  : 0.198589,
    'JOIN'  : 0.0569286,
}

atom_weights = {
    'B'     : 1.0,
    'C'     : 1.30428,
    #'C B'   : 1.35451,
    #'C I'   : 1.74145,
    'I'     : 2.21841,
    'Y'     : 2.2918,
    'K'     : 2.6654,
    'S'     : 2.69459,
    'J'     : 2.81965,
    'V'     : 2.87327,
    #'div'   : 3.06752,
    #'S B'   : 3.5036,
    'P'     : 3.69204,
    'F'     : 3.72682,
    #'S I'   : 4.12483,
    #'semi'  : 4.18665,
    'W'     : 4.36313,
    #'unit'  : 4.3634,
    #'W B'   : 4.3719,
    #'bool'  : 5.21614,
    #'W I'   : 6.21147,
    #'U'     : 6.3754,
    #'Simple': 10,
    #'prod'  : 12.0,
    #'sum'   : 12.0,
    #'maybe' : 12.0,
    #'sset'  : 12.0,
}

atom_prob = 1.0 - sum(compound_probs.values())
atom_probs = { key: -log(val) for key, val in atom_weights.iteritems() }
scale = atom_prob / sum(atom_probs.values())
for key in atom_probs.keys():
    atom_probs[key] *= scale

probs = {}
probs.update(compound_probs)
probs.update(atom_probs)


def make(outfile='skj.language'):
    lang = dict_to_language(probs)
    with open(outfile, 'wb') as f:
        outfile.write(lang.SerializeToString())


if __name__ == '__main__':
    make()
