import pomagma.analyst
from itertools import islice
from parsable import parsable
from pomagma.analyst.synthesize import FactsValidator
from pomagma.analyst.synthesize import is_complete
from pomagma.analyst.synthesize import iter_valid_sketches
from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_theory_string
from pomagma.compiler.sugar import desugar_expr

A_LANGUAGE = {
    'APP': 1.0,
    # 'COMP': 1.6,
    # 'JOIN': 3.0,
    'B': 1.0,
    'C': 1.3,
    'BOT': 2.0,
    'TOP': 2.0,
    'I': 2.2,
    # 'Y': 2.3,
    'K': 2.6,
    'S': 2.7,
    'J': 2.8,
    'DIV': 3.0,
}

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

    # and require that hole provide something new
    NLESS hole I
    NLESS hole APP K APP APP pair I I
    NLESS hole APP K APP APP pair pull push
    NLESS hole APP K APP APP pair raise lower
    '''
)


@parsable
def define_a(
        max_solutions=15,
        patience=pomagma.analyst.synthesize.PATIENCE,
        complete=True,
        verbose=False,
        address=pomagma.analyst.ADDRESS):
    '''
    Search for definition of A = Join {<s, r> | r o s [= I}.
    Tip: use pyprofile and snakeviz to profile this function:
    $ pyprofile -o define_a.pstats -s time src/examples/synthesize.py define_a
    $ snakeviz define_a.pstats
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
            language=A_LANGUAGE,
            patience=patience)
        if complete:
            valid_sketches = (r for r in valid_sketches if is_complete(r[-1]))
        results = sorted(islice(valid_sketches, 0, max_solutions))
    print 'Possible Fillings'
    for complexity, term, filling in results:
        print filling
    return results


if __name__ == '__main__':
    parsable()
