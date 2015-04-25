import re
from pomagma.compiler.compiler import compile_full
from pomagma.compiler.compiler import compile_given
from pomagma.compiler.compiler import get_events
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_0
from pomagma.compiler.expressions import Expression_1
from pomagma.compiler.expressions import Expression_2
from pomagma.compiler.plans import add_costs
from pomagma.compiler.sequents import Sequent


EQUAL = Expression_2('EQUAL')
LESS = Expression_2('LESS')
NLESS = Expression_2('NLESS')
CO = Expression_1('CO')
QUOTE = Expression_1('QUOTE')
APP = Expression_2('APP')
COMP = Expression_2('COMP')
JOIN = Expression_2('JOIN')
f = Expression_0('f')
g = Expression_0('g')
x = Expression_0('x')
y = Expression_0('y')
z = Expression_0('z')


outfile = None


def print_compiles(compiles):
    for cost, seq, plan in compiles:
        print '# cost = {0}'.format(cost)
        print '# infer {0}'.format(seq)
        print re.sub(': ', '\n', repr(plan))
        print


def _test_sequent(*args):
    sequent = Sequent(*args)
    print '-' * 78
    print 'Compiling full search: {0}'.format(sequent)
    compiles = compile_full(sequent)
    print_compiles(compiles)
    full_cost = add_costs(c for (c, _, _) in compiles)

    incremental_cost = None
    for event in get_events(sequent):
        print 'Compiling incremental search given: {0}'.format(event)
        compiles = compile_given(sequent, event)
        print_compiles(compiles)
        if event.args:
            cost = add_costs(c for (c, _, _) in compiles)
            if incremental_cost:
                incremental_cost = add_costs([incremental_cost, cost])
            else:
                incremental_cost = cost

    print '# full cost =', full_cost, 'incremental cost =', incremental_cost


def test_compile_I():
    I = Expression.make('I')
    _test_sequent(
        [],
        [EQUAL(APP(I, x), x)])


def test_compile_K():
    K = Expression.make('K')
    _test_sequent(
        [],
        [EQUAL(APP(APP(K, x), y), x)])


def test_compile_W():
    W = Expression.make('W')
    _test_sequent(
        [],
        [EQUAL(APP(APP(W, x), y), APP(APP(x, y), y))])


def test_compile_B_app():
    B = Expression.make('B')
    _test_sequent(
        [],
        [EQUAL(APP(APP(APP(B, x), y), z), APP(x, APP(y, z)))])


def test_compile_B_comp():
    B = Expression.make('B')
    _test_sequent(
        [],
        [EQUAL(APP(APP(B, x), y), COMP(x, y))])


def test_compile_app_comp():
    _test_sequent(
        [],
        [EQUAL(APP(COMP(x, y), z), APP(x, APP(y, z)))])


def test_compile_comp_assoc():
    _test_sequent(
        [],
        [EQUAL(COMP(COMP(x, y), z), COMP(x, COMP(y, z)))])


def test_compile_C():
    C = Expression.make('C')
    _test_sequent(
        [],
        [EQUAL(APP(APP(APP(C, x), y), z), APP(APP(x, z), y))])


def test_compile_S():
    # Compiling incremental search given: APP APP_x_y APP_y_z
    # cost = 2.70067540518
    # if S
    # for x let APP_S_x
    # for y if APP x y let APP_APP_S_x_y
    # for z if APP y z let APP_APP_APP_S_x_y_z
    # ensure EQUAL APP_APP_APP_S_x_y_z APP_APP_x_z_APP_y_z
    S = Expression.make('S')
    _test_sequent(
        [],
        [EQUAL(APP(APP(APP(S, x), y), z), APP(APP(x, z), APP(y, z)))])


def test_compile_Y():
    Y = Expression.make('Y')
    _test_sequent(
        [],
        [EQUAL(APP(Y, f), APP(f, APP(Y, f)))])


def test_compile_bot():
    BOT = Expression.make('BOT')
    _test_sequent(
        [],
        [LESS(BOT, x)])


def test_compile_reflexive():
    _test_sequent(
        [],
        [LESS(x, x)])


def test_compile_mono():
    _test_sequent(
        [LESS(x, y), LESS(f, g)],
        [LESS(APP(f, x), APP(g, y))])


def test_compile_mu():
    _test_sequent(
        [LESS(x, y)],
        [LESS(APP(f, x), APP(f, y))])


def test_compile_join_idem():
    _test_sequent(
        [],
        [EQUAL(JOIN(x, x), x)])


def test_compile_join_less():
    _test_sequent(
        [],
        [LESS(x, JOIN(x, y))])


def test_compile_co():
    # TODO use inverse iteration for injective_function::inverse_iterator
    # Compiling incremental search given: APP CO_x y
    # cost = 0.926425846749
    # for x if CO x let APP_y_x
    # ensure LESS APP_CO_x_y APP_y_x
    _test_sequent(
        [],
        [LESS(APP(CO(x), y), APP(y, x))])


def test_compile_comp_x_x_x():
    U = Expression.make('U')
    _test_sequent(
        [EQUAL(COMP(x, x), x)],
        [EQUAL(x, APP(U, x))])


def test_compile_eval():
    EVAL = Expression.make('EVAL')
    _test_sequent(
        [],
        [EQUAL(APP(EVAL, QUOTE(x)), x)])


def test_compile_qt_quote():
    QT = Expression.make('QT')
    _test_sequent(
        [],
        [EQUAL(APP(QT, QUOTE(x)), QUOTE(QUOTE(x)))])


def test_compile_ap_quote():
    AP = Expression.make('AP')
    _test_sequent(
        [],
        [EQUAL(APP(APP(AP, QUOTE(x)), QUOTE(y)), QUOTE(APP(x, y)))])
