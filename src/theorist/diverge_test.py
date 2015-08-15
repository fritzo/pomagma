from nose.tools import assert_equal, assert_raises
import pomagma.util
from pomagma.theorist.diverge import Converged
from pomagma.theorist.diverge import Diverged
from pomagma.theorist.diverge import I, K, F, B, C, W, S, Y, TOP
from pomagma.theorist.diverge import converge_step
from pomagma.theorist.diverge import iter_terms
from pomagma.theorist.diverge import parse_term
from pomagma.theorist.diverge import print_term
from pomagma.theorist.diverge import try_converge
from pomagma.theorist.diverge import try_prove_diverge
from pomagma.theorist.diverge import may_diverge
from pomagma.theorist.diverge import must_diverge


a, b, c = ('a',), ('b',), ('c',)  # argument lists
x, y, z = 'x', 'y', 'z'  # arguments


STEPS = [
    ((I,), (TOP,)),
    ((I, a,), a),
    ((I, (x,), a,), (x, a,)),

    ((K,), (TOP,)),
    ((K, a,), a),
    ((K, a, b,), a),
    ((K, (x,), b, c,), (x, c,)),

    ((F,), (TOP,)),
    ((F, a,), (TOP,)),
    ((F, a, b,), b),
    ((F, a, (x,), c,), (x, c,)),

    ((B,), (TOP,)),
    ((B, a,), a),
    ((B, (x,), (y,),), (x, (y, (TOP,),),)),
    ((B, (x,), (y,), a,), (x, (y, a,),)),
    ((B, (x,), (y,), a, b,), (x, (y, a,), b,)),

    ((C,), (TOP,)),
    ((C, a,), a),
    ((C, (x,), a,), (x, (TOP,), a,)),
    ((C, (x,), a, b,), (x, b, a,)),
    ((C, (x,), a, b, c,), (x, b, a, c,)),

    ((W,), (TOP,)),
    ((W, (x,),), (x, (TOP,), (TOP,),)),
    ((W, (x,), a,), (x, a, a,)),
    ((W, (x,), a, b,), (x, a, a, b,)),

    ((S,), (TOP,)),
    ((S, (x,),), (x, (TOP,), (TOP,),)),
    ((S, (x,), (y,),), (x, (TOP,), (y, (TOP,),),)),
    ((S, (x,), (y,), a,), (x, a, (y, a,),)),
    ((S, (x,), (y,), a, b,), (x, a, (y, a,), b,)),

    ((Y,), (TOP,)),
    ((Y, (x,),), (x, (Y, (x,),),)),
    ((Y, (x,), a,), (x, (Y, (x,),), a,)),
]


def _test_converge_step(term, expected):
    actual = converge_step(term)
    assert_equal(expected, actual)


def test_converge_step():
    for term, expected in STEPS:
        yield _test_converge_step, term, expected


def test_converge():
    assert_raises(Converged, converge_step, (TOP,))


def test_www_diverges():
    WWW = (W, (W,), (W,),)
    assert_equal(converge_step(WWW), WWW)
    assert_raises(Diverged, try_converge, WWW, 1)


def assert_diverges(string):
    steps = 10
    term = parse_term(string)
    assert_raises(Diverged, try_converge, term, steps)


def test_diverges():
    strings = [
        'APP APP W W W',
        'APP APP W W APP W W',
        'COMP Y CI',
        'COMP Y CB',
        'COMP Y APP S I',
        'COMP Y APP S W',
        'COMP Y APP S S',
    ]
    for string in strings:
        yield assert_diverges, string


def test_try_prove_diverge():
    atoms = [I, K, B, C, W, S]
    max_atom_count = 3
    max_steps = 20
    with pomagma.util.in_temp_dir():
        with open('source.facts', 'w') as f:
            f.write('# test terms')
            for term in iter_terms(atoms, max_atom_count):
                f.write('\n')
                f.write('EQUAL BOT {}'.format(print_term(term)))
        try_prove_diverge(
            'source.facts',
            'unproven.facts',
            'theorems.facts',
            max_steps)
        with open('theorems.facts') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if line.startswith('EQUAL BOT '):
                    term = parse_term(line[len('EQUAL BOT '):])
                    assert_raises(Diverged, try_converge, term, max_steps)
                elif line.startswith('NLESS ') and line.endswith(' BOT'):
                    term = parse_term(line[len('NLESS '): 1 - len(' BOT')])
                    assert_raises(Converged, try_converge, term, max_steps)
                elif line:
                    raise ValueError('Bad line:\n{}'.format(line))


def test_may_diverge():
    may_diverge


def test_must_diverge():
    must_diverge
