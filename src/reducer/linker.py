from pomagma.reducer import lib
from pomagma.reducer.code import free_vars
from pomagma.reducer.sugar import as_code
from pomagma.reducer.transforms import define, substitute


def bind(code, var, lazy=True):
    assert var[1].startswith('lib.')
    name = var[1][4:]
    defn = getattr(lib, name)  # raises AttributeError if not found.
    return (define if lazy else substitute)(var, as_code(defn), code)


def link(code, lazy=True):
    code = as_code(code)
    free = free_vars(code)
    to_bind = sorted(var for var in free if var[1].startswith('lib.'))
    for var in to_bind:
        code = bind(code, var, lazy=lazy)

    return code
