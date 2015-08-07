import pomagma.analyst
import parsable

theories = {}

theories['unit'] = '''
CLOSED t         -----------------   LESS APP f TOP APP g TOP
FIXES V t        EQUAL APP t x TOP   LESS APP f I APP g I
FIXES t I        EQUAL APP t x I     ------------------------
LESS APP J I t                       LESS COMP f t COMP g t
'''

theories['semi'] = '''
CLOSED t      -----------------   LESS APP f TOP APP g TOP
FIXES V t     EQUAL APP t x TOP   LESS APP f I APP g I
FIXES t BOT   EQUAL APP t x I     LESS APP f BOT APP g BOT
FIXES t I     EQUAL APP t x BOT   ------------------------
                                  LESS COMP f t COMP g t
'''

theories['bool'] = '''
CLOSED t      -----------------   LESS APP f TOP APP g TOP
FIXES V t     EQUAL APP t x TOP   LESS APP f K APP g K
FIXES t BOT   EQUAL APP t x K     LESS APP f F APP g F
FIXES t K     EQUAL APP t x F     LESS APP f BOT APP g BOT
FIXES t F     EQUAL APP t x BOT   ------------------------
                                  LESS COMP f t COMP g t
'''

theories['boool'] = '''
CLOSED t      -----------------   LESS APP f TOP APP g TOP
FIXES V t     EQUAL APP t x TOP   LESS APP f J APP g J
FIXES t BOT   EQUAL APP t x J     LESS APP f K APP g K
FIXES t K     EQUAL APP t x K     LESS APP f F APP g F
FIXES t F     EQUAL APP t x F     LESS APP f BOT APP g BOT
FIXES t J     EQUAL APP t x BOT   ------------------------
                                  LESS COMP f t COMP g t
'''


def print_solutions(var, theory, max_solutions):
    assert isinstance(var, basestring), var
    assert isinstance(theory, basestring), theory
    assert isinstance(max_solutions, (int, float)), max_solutions
    with pomagma.analyst.connect() as db:
        solutions = db.solve(var, theory)
    print 'Necessary:'
    for term in solutions['necessary']:
        print '  {}'.format(term)
    print 'Possible:'
    for term in solutions['possible']:
        print '  {}'.format(term)


@parsable.command
def define_unit(max_solutions=32):
    '''
    Conjecture definitions of UNIT.
    '''
    print_solutions('t', theories['unit'], max_solutions)


@parsable.command
def define_semi(max_solutions=32):
    '''
    Conjecture definitions of SEMI.
    '''
    print_solutions('t', theories['semi'], max_solutions)


@parsable.command
def define_bool(max_solutions=32):
    '''
    Conjecture definitions of BOOL.
    '''
    print_solutions('t', theories['bool'], max_solutions)


@parsable.command
def define_boool(max_solutions=32):
    '''
    Conjecture definitions of BOOOL.
    '''
    print_solutions('t', theories['boool'], max_solutions)


if __name__ == '__main__':
    parsable.dispatch()
