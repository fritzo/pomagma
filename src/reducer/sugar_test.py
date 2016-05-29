from pomagma.reducer import io
from pomagma.reducer.sugar import VAR, app, fun, program
from pomagma.util import TODO

x = VAR('x')
y = VAR('y')
z = VAR('z')


@program('num', 'num')
def succ(n):
    return io.succ(n)


@program(('prod', 'num', 'num'), 'num')
def add(xy):
    add = VAR('add')  # FIXME recurse
    return app(xy,
               fun(x, y, app(x, y, fun(z, io.succ(app(add, io.pair(z, y)))))))


@program(('prod', 'num', 'num'), 'bool')
def num_less(xy):
    TODO('return app(xy, fun(m, n, app(n, , ...)))')


@program(('list', 'num'), ('list', 'num'))
def list_num_sort(xs):
    TODO('implicit sort')
