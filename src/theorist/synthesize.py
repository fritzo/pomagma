import pomagma.analyst
from itertools import islice
from parsable import parsable
from pomagma.compiler.simplify import simplify
from pomagma.analyst.synthesize import iter_valid_sketches
from pomagma.analyst.compiler import unguard_vars
from pomagma.compiler.parser import parse_string_to_expr


def pair(x, y):
    return 'FUN f APP APP f {} {}'.format(x, y)


def conj(s, r):
    return 'FUN g COMP r COMP g s'


def join(*args):
    if not args:
        return 'BOT'
    args = reversed(args)
    result = args[0]
    for arg in args[1:]:
        result = 'JOIN {} {}'.format(arg, result)
    return result


class Context(object):
    def __init__(self, db, term, var):
        self._term = parse_string_to_expr(term)
        self._var = parse_string_to_expr(var)

    def __call__(self, filling):
        term = self._term.substitute(self._var, filling)
        term = simplify(term)
        term = self._db.simplify([term])[0]
        term = unguard_vars(term)
        return term


class Validator(object):
    def __init__(self, db, facts, var):
        self._validate = db.validate_facts
        self._facts = facts + [None]
        self._var = var

    def __call__(self, term):
        self._facts[-1] = 'EQUAL {} {}'.format(self._var, term)
        return self._validate(self._facts)


@parsable
def define_a(
        max_solutions=32,
        patience=pomagma.analyst.synthesize.PATIENCE,
        address=pomagma.analyst.ADDRESS):
    '''
    Search for definition of A = Join {<s, r> | r o s [= I}.
    '''
    assert max_solutions > 0, max_solutions
    assert patience > 0, patience
    a_def = 'APP Y FUN a {}'.format(join(
        pair('I', 'I'),
        pair('raise', 'lower'),
        pair('pull', 'push'),
        'APP a FUN s1 FUN r1 '
        'APP a FUN s2 FUN r2 {}'.format(
            pair('COMP s1 s2', 'COMP r2 r1')),
        'APP a FUN s1 FUN r1 '
        'APP a FUN s2 FUN r2 {}'.format(
            pair(conj('r1', 's2'), conj('s1', 'r2'))),
        'APP hole a',
    ))
    facts = [
        'EQUAL raise FUN x FUN y x',
        'EQUAL lower FUN x APP x TOP',
        'EQUAL pull FUN x FUN y JOIN x APP DIV y',
        'EQUAL push FUN x APP x BOT',
        'EQUAL A {}'.format(a_def),
        'LESS {} A'.format(pair('I', 'I')),
        'LESS {} A'.format(pair('raise', 'lower')),
        'LESS {} A'.format(pair('pull', 'push')),
        'LESS {} A'.format(
            'ABIND s1 r1 ABIND s2 r2 {}'.format(
                pair('COMP s1 s2', 'COMP r2 r1'))),
        'LESS {} A'.format(
            'ABIND s1 r1 ABIND s2 r2 {}'.format(
                pair('COMP s1 s2', 'COMP r2 r1'))),
    ]
    with pomagma.analyst.connect(address) as db:
        context = Context(db, a_def, 'hole')
        validate = Validator(db, facts, 'a_def')
        valid_sketches = iter_valid_sketches(context, validate, patience)
        results = sorted(islice(valid_sketches, 0, max_solutions))
    print 'Possible Fillings'
    for complexity, term, filling in results:
        print filling
    return results


if __name__ == '__main__':
    parsable()
