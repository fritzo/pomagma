"""Eager linear reduction of term graphs.

This library intends to generalize reducer.bohm operations to reducer.graph
data structures.

"""

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer import syntax
from pomagma.reducer.graphs import (_ABS, _APP, _JOIN, _NVAR, _TOP, _VAR, APP,
                                    BOT, FUN, JOIN, NVAR, TOP, Graph,
                                    extract_subterm, graph_make, isa_abs,
                                    isa_app, isa_join, iter_join,
                                    preprocess_join_args)
from pomagma.reducer.util import UnreachableError
from pomagma.util import TODO

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')

I = FUN(x, x)
K = FUN(x, FUN(y, x))
B = FUN(x, FUN(y, FUN(z, APP(x, APP(y, z)))))
C = FUN(x, FUN(y, FUN(z, APP(APP(x, z), y))))
S = FUN(x, FUN(y, FUN(z, APP(APP(x, z), APP(y, z)))))

KI = FUN(x, FUN(y, y))
CB = FUN(x, FUN(y, FUN(z, APP(y, APP(x, z)))))
CI = FUN(x, FUN(y, APP(y, x)))

true = K
false = KI


# ----------------------------------------------------------------------------
# Functional programming

@memoize_args
def substitute(graph, value):
    """Substitute value for VAR() in term.

    This is linear-eager, and will be lazy about nonlinear
    substitutions.

    """
    terms = list(graph)
    shifted_values = {0: value}
    value_roots = []
    # for term in value:
    #     terms.append(term_shift(term, value_root))
    updated = {}
    pending = set([(0, 0, 0)])
    while pending:
        root, value_rank, rank = pending.pop()
        term = terms[root]
        symbol = term[0]
        if symbol in (_TOP, _NVAR):
            updated[root] = root
        elif symbol is _VAR:
            if term[1] != rank:
                updated[root] = root
            else:
                while value_rank not in shifted_values:
                    max_rank = max(shifted_values)
                    max_value = shifted_values[max_rank]
                    TODO('deal with cycles')
                    # shifted_values[max_rank + 1] = increment_rank(max_value)
                    shifted_values[max_rank + 1] = max_value
                while value_rank < len(shifted_values):
                    TODO()
                updated[root] = value_roots[value_rank]
        elif symbol is _APP:
            TODO()
        elif symbol is _ABS:
            TODO()
        elif symbol is _JOIN:
            TODO()
        else:
            raise ValueError(term)
    TODO('apply updated dict to terms')
    return graph_make(terms)


@memoize_args
def app(fun, arg):
    """Apply function to argument and linearly reduce."""
    if fun is TOP:
        return TOP
    elif isa_abs(fun):
        # Linear beta reduce.
        body = extract_subterm(fun, fun[0][1])
        return substitute(body, arg)
    elif isa_join(fun):
        # Distribute APP over JOIN.
        return join(app(g, arg) for g in iter_join(fun))
    else:
        return APP(fun, arg)
    raise UnreachableError((fun, arg))


@memoize_args
def abstract(var, graph):
    """Abstract a named variable and simplify."""
    TODO()
    if graph is TOP:
        return TOP
    elif isa_app(graph):
        # fun = extract_subterm(graph, graph[0][1])
        # arg = extract_subterm(graph, graph[0][2])
        TODO('test for self-reference and eta-contract')
        return FUN(graph)
    elif isa_join(graph):
        # Distribute ABS over JOIN.
        return join(abstract(g) for g in iter_join(graph))
    else:
        return FUN(graph)
    raise UnreachableError(graph)


# ----------------------------------------------------------------------------
# Scott ordering

@preprocess_join_args
@memoize_arg
def join(args):
    # Handle trivial cases.
    if TOP in args:
        return TOP
    if len(args) == 1:
        return next(iter(args))

    # Filter out strictly dominated terms (requires transitivity).
    filtered = [
        arg for arg in args
        if not any(dominates(ub, arg) for ub in args if ub is not arg)
    ]

    # Construct a join term.
    return JOIN(filtered)


def dominates(lhs, rhs):
    """Weak strict domination relation: lhs =] rhs and lhs [!= rhs."""
    lhs_rhs = try_decide_less(lhs, rhs)
    rhs_lhs = try_decide_less(rhs, lhs)
    return rhs_lhs is True and lhs_rhs is False


@memoize_args
def try_decide_less(lhs, rhs):
    """Weak decision procedure returning True, False, or None."""
    assert isinstance(lhs, Graph), lhs
    assert isinstance(rhs, Graph), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    if lhs is TOP and rhs is BOT:
        return False

    # TODO Try harder.

    # Give up.
    return None


# ----------------------------------------------------------------------------
# Conversion

SIGNATURE = {
    'TOP': TOP,
    'BOT': BOT,
    'NVAR': NVAR,
    'APP': app,
    'JOIN': join,
    'FUN': abstract,
    'I': I,
    'K': K,
    'B': B,
    'C': C,
    'S': S,
}

convert = syntax.Transform(**SIGNATURE)