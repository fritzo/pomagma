"""Program synthesis by sketching for untyped combinatory algebra.

This implements an algorithm to solve general recursive sets of inequalities
involving partial terms (i.e. terms with holes, sketches) by filling in holes.
The inputs are:
- a set of inequality constraints,
- a sketch with holes to fill, and
- a probabilistic language to generate hole fillings.
The output is an any-time stream of possibly-valid terms.
The algorithm is complete but not sound, in that every valid solution will
eventually be yielded, but some yielded solutions may be invalid.

The algorithm is structured as a multi-stage pipeline.
At each stage, solutions are filtered out and quotiented down (deduplicated),
and many computations are cached (memoized).

The pipeline stages are:
1. Generate a stream of hole-fillings, filtered to remove duplicates.
2. Quotient out by normalizing the fillings, and deduplicate.
3. Filter out strict narrowings of previously invalidated fillings.
4. Substitute the filling into a context; quotient by simplifying; and dedup.
5. Filter out contexts by client-side validation, which is heavily memoized.
6. Filter out contexts by server-side constraint propagation, also memoized.
7. Optionally filter out fillings with holes, i.e., restrict to ground terms.

"""

import heapq
import itertools
import signal
import sys
import time

import psutil

from pomagma.analyst.client import VALIDATE_POLL_SEC
from pomagma.analyst.compiler import unguard_vars
from pomagma.compiler.expressions import Expression, Expression_2
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.signature import get_arity, get_nargs
from pomagma.compiler.simplify import simplify_expr
from pomagma.compiler.sugar import desugar_expr
from pomagma.compiler.util import inputs, intern_keys, memoize_args

MAX_MEMORY = 0.95
MAX_SOLUTIONS = 10
INFINITY = float("inf")
HOLE = Expression("HOLE")
BOT = Expression("BOT")
I = Expression("I")
EQUAL = Expression_2("EQUAL")

format_invalid = "\033[31mInvalid:\033[0m %s".__mod__
format_partial = "\033[33mPartial:\033[0m %s".__mod__
format_complete = "\033[32;1mComplete:\033[0m %s".__mod__


# ----------------------------------------------------------------------------
# streams of sketches


@inputs(Expression)
def is_complete(expr):
    return expr is not HOLE and all(is_complete(arg) for arg in expr.args)


class ComplexityEvaluator:
    def __init__(self, language):
        assert isinstance(language, dict), language
        for name, cost in list(language.items()):
            assert isinstance(name, str), name
            assert isinstance(cost, float), cost
            assert cost > 0, cost
        language = language.copy()
        language["HOLE"] = 0.0
        self._language = intern_keys(language)

    def __call__(self, term):
        assert isinstance(term, Expression)
        return sum(self._language.get(n, INFINITY) for n in term.polish.split())


def make_template(name):
    assert isinstance(name, str), name
    holes = [HOLE] * get_nargs(get_arity(name))
    return Expression(name, *holes)


class NaiveHoleFiller:
    """A more intelligent hole filler would only enumerate normal forms."""

    def __init__(self, language):
        assert isinstance(language, dict), language
        assert all(isinstance(n, str) for n in language), language
        self._fillings = tuple(make_template(n) for n in sorted(language))

    @memoize_args
    def __call__(self, term):
        nargs = len(term.args)
        if nargs == 0:
            return self._fillings if term is HOLE else ()
        if nargs == 1:
            name = term.name
            (key,) = term.args
            return tuple(Expression(name, f) for f in self(key))
        if nargs == 2:
            name = term.name
            lhs, rhs = term.args
            return tuple(
                itertools.chain(
                    (Expression(name, f, rhs) for f in self(lhs)),
                    (Expression(name, lhs, f) for f in self(rhs)),
                )
            )
        return None


class UniquePriorityQueue:
    """Duplicates may be pushed, but will only be poppoed once.

    The least-priority item is popped. Implementation assumes that items will
    be pushed more often than popped, so that the queue never becomes empty,
    hence there is no test for emptiness.

    """

    def __init__(self, priority):
        assert callable(priority), priority
        self._priority = priority
        self._to_pop = []
        self._pushed = set()

    def push(self, item):
        if item not in self._pushed:
            self._pushed.add(item)
            heapq.heappush(self._to_pop, (self._priority(item), item))

    def pop(self):
        assert self._to_pop, "cannot pop from empty queue"
        return heapq.heappop(self._to_pop)[1]


def iter_sketches(priority, fill_holes, initial_sketch=HOLE):
    """
    priority : term -> float
    fill_holes : term -> list(term), must increase priority, decrease validity
    """
    assert callable(priority), priority
    assert callable(fill_holes), fill_holes
    assert isinstance(initial_sketch, Expression), initial_sketch
    queue = UniquePriorityQueue(priority)
    queue.push(initial_sketch)
    while True:
        sketch = queue.pop()
        steps = fill_holes(sketch)
        for step in steps:
            queue.push(step)
        yield sketch, steps


def filter_normal_sketches(sketches):
    """Filter out sketches whose normal forms have already been seen."""
    normal_forms = set()
    for sketch, steps in sketches:
        normal = simplify_expr(sketch)
        if normal not in normal_forms:
            normal_forms.add(normal)
            yield sketch, steps


def lazy_iter_valid_sketches(fill, lazy_validate, normal_sketches, verbose=0):
    """Yield (state, term) pairs and Nones; consumers should filter out Nones.
    Since satisfiability is undecidable, consumers must decide when to give up.

    fill : term -> state, substitutes sketches into holes and simplifies
    lazy_validate : state -> bool or None, must be sound, may be incomplete
    sketches : stream(sketch:term, steps:list(term))

    """
    assert callable(fill), fill
    assert callable(lazy_validate), lazy_validate
    invalid_sketches = set()
    invalid_states = set()
    valid_states = set()
    for sketch, steps in normal_sketches:
        if sketch in invalid_sketches:
            invalid_sketches.update(steps)  # propagate
            yield
            continue
        state = fill(sketch)
        if state in valid_states:
            yield
            continue
        valid = False if state in invalid_states else lazy_validate(state)
        while valid is None:
            yield
            time.sleep(VALIDATE_POLL_SEC)
            valid = lazy_validate(state)
        if not valid:
            invalid_states.add(state)
            invalid_sketches.update(steps)  # propagate
            if verbose >= 3:
                print(format_invalid(sketch))
            yield
            continue

        valid_states.add(state)
        if verbose >= 1:
            if is_complete(sketch):
                print(format_complete(sketch))
            elif verbose >= 2:
                print(format_partial(sketch))
        yield state, sketch


class Interruptable:
    def __enter__(self):
        self._interrupted = False
        self._old_handler = signal.signal(signal.SIGINT, self)
        return self

    def __exit__(self, type, value, traceback):
        if self._old_handler is not None:
            signal.signal(signal.SIGINT, self._old_handler)

    def __call__(self, sig, frame):
        signal.signal(signal.SIGINT, self._old_handler)
        self._old_handler = None
        self._interrupted = True

    def poll(self):
        if self._interrupted:
            sys.stderr.write("\nReceived SIGINT\n")
            sys.stderr.flush()
            raise StopIteration


def polling_iterator(lazy_iterator, max_memory):
    """Filter results of a lazy_iterator until either memory runs out or
    SIGINT.

    Patience is measured in nebulous "progress steps".

    """
    assert isinstance(max_memory, float), max_memory
    assert 0 < max_memory and max_memory < 1, max_memory
    with Interruptable() as interrupted:
        for value_or_none in lazy_iterator:
            interrupted.poll()
            if psutil.virtual_memory().percent > max_memory * 100:
                sys.stderr.write("Reached memory limit\n")
                sys.stderr.flush()
                raise StopIteration
            if value_or_none is not None:
                yield value_or_none


# this ties everything together
def iter_valid_sketches(
    fill, lazy_validate, language, initial_sketch=HOLE, max_memory=MAX_MEMORY, verbose=0
):
    """
    Yield (complexity, term, sketch) tuples until memory runs out or Ctrl-C.

    fill : term -> state, substitutes sketches into holes and simplifies
    lazy_validate : state -> bool or None, must be sound, may be incomplete
    language : dict(name:str -> cost:float), costs must be positive
    initial_sketch : term, must have at least one hole
    max_memory : float, max portion of memory, in [0,1]
    """
    assert callable(fill), fill
    assert callable(lazy_validate), lazy_validate
    assert isinstance(language, dict), language
    assert all(isinstance(n, str) for n in language), language
    assert isinstance(initial_sketch, Expression), initial_sketch
    assert isinstance(max_memory, float), max_memory
    assert 0 < max_memory and max_memory < 1, max_memory
    complexity = ComplexityEvaluator(language)
    fill_holes = NaiveHoleFiller(language)
    sketches = iter_sketches(complexity, fill_holes, initial_sketch)
    sketches = filter_normal_sketches(sketches)
    lazy_valid_sketches = lazy_iter_valid_sketches(
        fill, lazy_validate, sketches, verbose=verbose
    )
    for term, sketch in polling_iterator(lazy_valid_sketches, max_memory):
        yield complexity(sketch), term, sketch  # suitable for sort()


# ----------------------------------------------------------------------------
# fillers and validators


@memoize_args
def _db_simplify_expr(db, expr):
    string = db.simplify([expr.polish])[0]
    expr = parse_string_to_expr(string)
    return unguard_vars(expr)


@inputs(object, Expression)
def simplify_filling(db, term):
    term = simplify_expr(term)
    return _db_simplify_expr(db, term)


def is_def(fact):
    return fact.name == "EQUAL" and fact.args[0].is_var()


@inputs(set, dict)
def extract_defs_from_facts(facts, defs):
    for fact in list(facts):
        if is_def(fact):
            facts.remove(fact)
            var, body = fact.args
            defs.setdefault(var, set()).add(body)


@inputs(set, Expression, set)
def substitute_bodies(terms, var, bodies):
    for term in list(terms):
        if var in term.vars:
            terms.remove(term)
            for body in bodies:
                terms.add(simplify_expr(term.substitute(var, body)))


def simplify_defs(facts, vars_to_keep=set()):
    """Substitute all facts of form 'EQUAL var closed_term' into remaining
    facts.

    In case of multiple equivalent definitions, all combinations of
    substitutions will be added. This generally reduces the number of
    free variables.

    """
    facts = {desugar_expr(f) for f in facts}
    defs = {}
    extract_defs_from_facts(facts, defs)
    changed = True
    while changed:
        changed = False
        for var, bodies in list(defs.items()):
            if any(v in defs for b in bodies for v in b.vars):
                continue  # avoid substitution cycles
            if not any(var in b.vars for bs in list(defs.values()) for b in bs):
                if not any(var in f.vars for f in facts):
                    continue
            if var not in vars_to_keep:
                del defs[var]
            substitute_bodies(facts, var, bodies)
            for var2, bodies2 in list(defs.items()):
                substitute_bodies(bodies2, var, bodies)
            extract_defs_from_facts(facts, defs)
            changed = True
    for var, bodies in list(defs.items()):
        facts.update(EQUAL(var, b) for b in bodies)
    return facts


def simplify_facts(db, facts, vars_to_keep):
    assert isinstance(facts, list), facts
    assert all(isinstance(f, Expression) for f in facts), facts
    assert isinstance(vars_to_keep, set), vars_to_keep
    assert all(isinstance(v, Expression) for v in vars_to_keep), vars_to_keep
    assert all(v.is_var() for v in vars_to_keep), vars_to_keep
    facts = {simplify_expr(f) for f in facts}
    facts = simplify_defs(facts, vars_to_keep)
    strings = db.simplify([f.polish for f in facts])
    facts = {parse_string_to_expr(s) for s in strings}
    return list(map(unguard_vars, facts))


class FactsValidator:
    def __init__(self, db, facts, var, initial_sketch=HOLE):
        assert isinstance(facts, list), facts
        assert all(isinstance(f, Expression) for f in facts), facts
        assert isinstance(var, Expression), var
        assert var.is_var(), var
        facts = simplify_facts(db, facts, initial_sketch.vars)
        self._db = db
        self._facts = facts
        self._var = var

    def fill(self, filling):
        return simplify_filling(self._db, filling)

    def lazy_validate(self, filling):
        facts = [f.substitute(self._var, filling) for f in self._facts]
        facts = simplify_facts(self._db, facts, set())
        truthy = I  # facts proven true
        falsey = BOT  # facts proven false
        unknown_facts = []
        for fact in facts:
            if fact is falsey:
                return False
            if fact is truthy:
                continue
            unknown_facts.append(fact)
        facts = unknown_facts
        strings = [f.polish for f in facts]
        return self._db.validate_facts(strings, block=False)


# this ties everything together
def synthesize_from_facts(
    db,
    facts,
    var,
    language,
    initial_sketch,
    max_solutions=MAX_SOLUTIONS,
    max_memory=MAX_MEMORY,
    verbose=0,
):
    """Synthesize a list of sketches which replace `var` in `facts` by filling
    in HOLEs in an `initial_sketch` with terms generated from a `langauge`."""
    assert isinstance(facts, list), facts
    assert all(isinstance(f, Expression) for f in facts), facts
    assert isinstance(var, Expression), var
    assert isinstance(language, dict), language
    assert isinstance(initial_sketch, Expression), initial_sketch
    assert isinstance(max_solutions, int), max_solutions
    assert max_solutions > 0
    assert isinstance(max_memory, float), max_memory
    assert 0 < max_memory and max_memory < 1, max_memory
    validator = FactsValidator(
        db=db, facts=facts, var=var, initial_sketch=initial_sketch
    )
    valid_sketches = iter_valid_sketches(
        fill=validator.fill,
        lazy_validate=validator.lazy_validate,
        language=language,
        initial_sketch=initial_sketch,
        max_memory=max_memory,
        verbose=verbose,
    )
    valid_sketches = (r for r in valid_sketches if is_complete(r[-1]))
    return sorted(itertools.islice(valid_sketches, 0, max_solutions))
