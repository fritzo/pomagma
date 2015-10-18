import cProfile
import os
import pomagma.analyst
import pstats
from itertools import islice
from parsable import parsable
from pomagma.analyst.synthesize import FactsValidator
from pomagma.analyst.synthesize import iter_valid_sketches
from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_theory_string
from pomagma.compiler.sugar import desugar_expr
from pomagma.language.util import dict_to_language
from pomagma.language.util import json_load
from pomagma.util import SRC

SKJ = dict_to_language(json_load(os.path.join(SRC, 'language/skj.json')))

A_THEORY = (
    '''
    EQUAL pair FUN x FUN y FUN f APP APP f x y
    EQUAL conj FUN s FUN r FUN f COMP r COMP f s
    EQUAL conj FUN s FUN r FUN f COMP COMP r f s
    EQUAL raise FUN x FUN y x
    EQUAL lower FUN x APP x TOP
    EQUAL pull FUN x FUN y JOIN x APP DIV y
    EQUAL push FUN x APP x BOT

    # the existing A rules
    LESS APP APP pair I I A
    LESS APP APP pair pull push A
    LESS APP APP pair raise lower A
    LESS ABIND s1 r1 ABIND s2 r2 APP APP pair COMP s1 s2 COMP r2 r1 A
    LESS ABIND s1 r1 ABIND s2 r2'''
    ''' APP APP pair APP APP conj r1 s2 APP APP conj s1 r2 A

    # we search for an additional fixed point operation
    LESS APP hole A A
    '''
)


@parsable
def define_a(
        max_solutions=32,
        patience=pomagma.analyst.synthesize.PATIENCE,
        verbose=True,
        address=pomagma.analyst.ADDRESS):
    '''
    Search for definition of A = Join {<s, r> | r o s [= I}.
    '''
    assert max_solutions > 0, max_solutions
    assert patience > 0, patience
    facts = parse_theory_string(A_THEORY)['facts']
    facts = map(desugar_expr, facts)
    for fact in facts:
        for var in fact.vars:
            assert len(var.name) > 2, 'unbound variable: {}'.format(var)
    hole = Expression('hole')
    with pomagma.analyst.connect(address) as db:
        validator = FactsValidator(db, facts, hole, verbose=verbose)
        valid_sketches = iter_valid_sketches(
            fill=validator.fill,
            validate=validator.validate,
            free_vars=validator.free_vars(),
            language=SKJ,
            patience=patience)
        results = sorted(islice(valid_sketches, 0, max_solutions))
    print 'Possible Fillings'
    for complexity, term, filling in results:
        print filling
    return results


@parsable
def profile_a(
        saveto='profile_a.pstats',
        loadfrom=None,
        max_solutions=32,
        patience=pomagma.analyst.synthesize.PATIENCE,
        address=pomagma.analyst.ADDRESS,):
    '''
    Profile synthesis algorithm via define_a command.
    '''
    if loadfrom is None:
        command = 'define_a({}, {}, False, "{}")'.format(
            max_solutions,
            patience,
            address)
        print 'profiling {}'.format(command)
        cProfile.runctx(command, {'define_a': define_a}, None, saveto)
        loadfrom = saveto
    stats = pstats.Stats(loadfrom)
    stats.strip_dirs()
    stats.sort_stats('time')
    stats.print_stats(50)


if __name__ == '__main__':
    parsable()
