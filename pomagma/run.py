import re
import parsable
from pomagma import parser, compiler
from pomagma.compiler import (
    Variable,
    Function,
    Sequent,
    add_costs,
    )


def print_compiles(compiles):
    for cost, strategy in compiles:
        print '# cost = {0}'.format(cost)
        print re.sub(': ', '\n', repr(strategy))
        print


def measure_sequent(sequent):
    print '-' * 78
    print 'Compiling full search: {0}'.format(sequent)
    compiles = sequent.compile()
    print_compiles(compiles)
    full_cost = add_costs(*[cost for cost, _ in compiles])

    incremental_cost = None
    for event in sequent.get_events():
        print 'Compiling incremental search given: {0}'.format(event)
        compiles = sequent.compile_given(event)
        print_compiles(compiles)
        if event.children:
            cost = add_costs(*[cost for cost, _ in compiles])
            if incremental_cost:
                incremental_cost = add_costs(incremental_cost, cost)
            else:
                incremental_cost = cost

    print '# full cost =', full_cost, 'incremental cost =', incremental_cost


@parsable.command
def contrapositves(*filenames):
    '''
    Close rules under contrapositve
    '''
    sequents = []
    for filename in filenames:
        sequents += parser.parse(filename)
    for sequent in sequents:
        print sequent.ascii()
        print
        for neg in sequent.contrapositives():
            print neg.ascii(indent=4)
            print


@parsable.command
def measure(*filenames):
    '''
    Measure complexity of rules in files
    '''
    sequents = []
    for filename in filenames:
        sequents += parser.parse(filename)
    for sequent in sequents:
        measure_sequent(sequent)


@parsable.command
def report(*filenames):
    '''
    Make report.html of rule complexity in files
    '''
    TODO('write sequents to file, coloring by incremental complexity')


if __name__ == '__main__':
    parsable.dispatch()
