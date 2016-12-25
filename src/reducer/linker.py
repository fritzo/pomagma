from pomagma.reducer import lib
from pomagma.reducer.syntax import free_vars
from pomagma.reducer.curry import substitute
from pomagma.reducer.sugar import as_code


def bind(code, var):
    assert var[1].startswith('lib.')
    name = var[1][4:]
    defn = getattr(lib, name)  # raises AttributeError if not found.
    return substitute(var, as_code(defn), code)


def link(code):
    code = as_code(code)
    free = free_vars(code)
    to_bind = sorted(var for var in free if var[1].startswith('lib.'))
    for var in to_bind:
        code = bind(code, var)

    return code
