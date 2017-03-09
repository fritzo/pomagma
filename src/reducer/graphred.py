"""Eager linear reduction of term graphs.

This library intends to generalize reducer.bohm operations to reducer.graph
data structures.

"""

import inspect

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer import syntax
from pomagma.reducer.graphs import (_ABS, _APP, _JOIN, _NVAR, _TOP, _VAR, APP,
                                    BOT, FUN, JOIN, NVAR, TOP, Graph,
                                    extract_subterm, graph_make, iter_join,
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

def _var_is_linear(graph, var_pos):
    """Whether no terms of a graph ever copy the given bound variable."""
    assert isinstance(graph, Graph)
    assert isinstance(var_pos, int)
    assert 0 <= var_pos and var_pos < len(graph)
    assert graph[var_pos].is_var
    counts = [0] * len(graph)
    counts[var_pos] = 1

    # Propagate in reverse order.
    # Most graphs should converge after two iterations.
    schedule = [
        (i, term)
        for i, term in enumerate(graph)
        if term[0] not in (_TOP, _NVAR, _VAR)
    ]
    schedule.reverse()

    # Propagate until convergence.
    changed = True
    while changed:
        changed = False
        for i, term in schedule:
            symbol = term[0]
            if symbol is _ABS:
                count = counts[term[1]]
            elif symbol is _APP:
                count = counts[term[1]] + counts[term[2]]
            elif symbol is _JOIN:
                if len(term) == 1:
                    count = 0
                else:
                    count = max(counts[j] for j in term[1:])
            else:
                raise UnreachableError(symbol)
            if count > 1:
                return False
            if count != counts[i]:
                counts[i] = count
                changed = True
    return True


@memoize_arg
def is_linear(graph):
    """Whether no terms of a graph ever copy any bound variable.

    Note that JOIN is not considered copying.
    """
    assert isinstance(graph, Graph)
    return all(
        _var_is_linear(graph, pos)
        for pos, var in enumerate(graph)
        if var.is_var
    )


@memoize_args
def substitute(graph, value):
    """Substitute value for VAR() in graph.

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
    assert isinstance(fun, Graph), fun
    assert isinstance(arg, Graph), arg
    if fun is TOP:
        return TOP
    elif fun.is_abs:
        # Linear beta reduce.
        body = extract_subterm(fun, fun[0][1])
        return substitute(body, arg)
    elif fun.is_join:
        # Distribute APP over JOIN.
        return join(app(g, arg) for g in iter_join(fun))
    else:
        return APP(fun, arg)
    raise UnreachableError((fun, arg))


def graph_apply(fun, *args):
    """Currying wrapper around reducer.graphred.app(-,-)."""
    result = fun
    for arg in args:
        arg = as_graph(arg)
        result = app(result, arg)
    return result


Graph.__call__ = graph_apply


@memoize_args
def abstract(var, graph):
    """Abstract a named variable and simplify."""
    assert isinstance(var, Graph) and var.is_nvar, var
    assert isinstance(graph, Graph), graph
    if graph is TOP:
        return TOP
    elif graph.is_join:
        # Distribute ABS over JOIN.
        return join(abstract(var, g) for g in iter_join(graph))
    else:
        result = FUN(var, graph)
        # TODO eta contract.
        return result
    raise UnreachableError(graph)


def as_graph(fun):
    """Convert lambdas to graphs using Higher Order Abstract Syntax [1].

    [1] Pfenning, Elliot (1988) "Higher-order abstract syntax"
      https://www.cs.cmu.edu/~fp/papers/pldi88.pdf
    """
    if isinstance(fun, Graph):
        return fun
    if not callable(fun):
        raise SyntaxError('Expected callable, got: {}'.format(fun))
    args, vargs, kwargs, defaults = inspect.getargspec(fun)
    if vargs or kwargs or defaults:
        source = inspect.getsource(fun)
        raise SyntaxError('Unsupported signature: {}'.format(source))
    symbolic_args = map(NVAR, args)
    symbolic_result = fun(*symbolic_args)
    graph = as_graph(symbolic_result)
    for var in reversed(symbolic_args):
        graph = abstract(var, graph)
    return graph


# ----------------------------------------------------------------------------
# Scott ordering

@preprocess_join_args
@memoize_arg
def join(args):
    if not isinstance(args, set):
        args = set(args)
    for arg in args:
        assert isinstance(arg, Graph), arg

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


def graph_join(lhs, rhs):
    rhs = as_graph(rhs)
    return join(set([lhs, rhs]))


Graph.__or__ = graph_join


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
    'JOIN': graph_join,
    'FUN': abstract,
    'I': I,
    'K': K,
    'B': B,
    'C': C,
    'S': S,
}

convert = syntax.Transform(**SIGNATURE)
