import heapq
import itertools
import math
import signal
from pomagma.analyst.compiler import unguard_vars
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_2
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.simplify import simplify_expr
from pomagma.compiler.sugar import desugar_expr
from pomagma.compiler.util import inputs
from pomagma.compiler.util import intern_keys
from pomagma.compiler.util import memoize_args
from pomagma.compiler.util import union
from pomagma.language.util import Language
from pomagma.language.util import language_to_dict

PATIENCE = 10000
HOLE = Expression.make('HOLE')
BOT = Expression.make('BOT')
I = Expression.make('I')
EQUAL = Expression_2('EQUAL')


class ComplexityEvaluator(object):
    def __init__(self, language, free_vars=[]):
        assert isinstance(language, Language), language
        assert isinstance(free_vars, list), free_vars
        signature = {t.name: -math.log(t.weight) for t in language.terms}
        if free_vars:
            var_count = len(free_vars)
            var_cost = math.log(var_count) + self._signature['APP']
            for var in free_vars:
                signature[var.name] = var_cost
        signature['HOLE'] = 0.0
        self._signature = intern_keys(signature)

    def __call__(self, term):
        assert isinstance(term, Expression)
        return sum(self._signature[n] for n in term.polish.split())


class NaiveHoleFiller(object):
    'A more intelligent hole filler would only enumerate normal forms'
    def __init__(self, language, free_vars):
        assert isinstance(language, Language), language
        assert isinstance(free_vars, list), free_vars
        assert all(isinstance(v, Expression) for v in free_vars), free_vars
        fillings = []
        grouped = language_to_dict(language)
        for name in sorted(grouped.get('NULLARY', [])):
            fillings.append(Expression.make(name))
        for name in sorted(grouped.get('INJECTIVE', [])):
            fillings.append(Expression.make(name, HOLE))
        for name in sorted(grouped.get('BINARY', [])):
            fillings.append(Expression.make(name, HOLE, HOLE))
        for name in sorted(grouped.get('SYMMETRIC', [])):
            fillings.append(Expression.make(name, HOLE, HOLE))
        for var in sorted(free_vars):
            fillings.append(var)
        self._fillings = tuple(fillings)

    @memoize_args
    def __call__(self, term):
        if term == HOLE:
            return self._fillings
        elif len(term.args) == 1:
            name = term.name
            key, = term.args
            return tuple(Expression.make(name, f) for f in self(key))
        elif len(term.args) == 2:
            name = term.name
            lhs, rhs = term.args
            return tuple(itertools.chain(
                (Expression.make(name, f, rhs) for f in self(lhs)),
                (Expression.make(name, lhs, f) for f in self(rhs)),
            ))
        else:
            return ()


class UniquePriorityQueue(object):
    '''
    Duplicates may be pushed, but will only be poppoed once.
    The least-priority item is popped.
    '''
    def __init__(self, priority):
        assert callable(priority), priority
        self._priority = priority
        self._to_pop = []
        self._pushed = set()

    def push(self, item):
        if item not in self._pushed:
            self._pushed.add(item)
            priority = self._priority(item)
            heapq.heappush(self._to_pop, (priority, item))

    def pop(self):
        assert self._to_pop, 'cannot pop from empty queue'
        return heapq.heappop(self._to_pop)[1]


def iter_sketches(priority, fill_holes):
    '''
    priority : term -> float
    fill_holes : term -> list(term), must increase priority, decrease validity
    '''
    assert callable(priority), priority
    assert callable(fill_holes), fill_holes
    queue = UniquePriorityQueue(priority)
    queue.push(HOLE)
    while True:
        sketch = queue.pop()
        steps = fill_holes(sketch)
        for step in steps:
            queue.push(step)
        yield sketch, steps


def filter_normal_sketches(sketches):
    '''
    Filter out sketches whose normal forms have already been seen.
    '''
    normal_forms = set()
    for sketch, steps in sketches:
        normal = simplify_expr(sketch)
        if normal not in normal_forms:
            normal_forms.add(normal)
            yield sketch, steps


def lazy_iter_valid_sketches(fill, validate, normal_sketches):
    '''
    Yield (state, term) pairs and Nones; consumers should filter out Nones.
    Since satisfiability is undecidable, consumers must decide when to give up.

    fill : term -> state, substitutes sketches into holes and simplifies
    validate : state -> bool, must be sound, may be incomplete
    sketches : stream(sketch:term, steps:list(term))
    '''
    assert callable(fill), fill
    assert callable(validate), validate
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
        if state in invalid_states or not validate(state):
            invalid_states.add(state)
            invalid_sketches.update(steps)  # propagate
            yield
            continue

        valid_states.add(state)
        yield state, sketch


class Interruptable(object):
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
            raise StopIteration


def impatient_iterator(lazy_iterator, patience=PATIENCE):
    '''
    Filter results of a lazy_iterator until either patience runs out or SIGINT.
    Patience is measured in nebulous "progress steps".
    '''
    assert patience > 0, patience
    patience_remaining = patience
    with Interruptable() as interrupted:
        for value_or_none in lazy_iterator:
            interrupted.poll()
            if value_or_none is not None:
                patience_remaining = patience
                yield value_or_none
            else:
                patience_remaining -= 1
                if patience_remaining == 0:
                    raise StopIteration


# this ties everything together
def iter_valid_sketches(
        fill,
        validate,
        language,
        free_vars=[],
        patience=PATIENCE):
    '''
    Yield (complexity, term, sketch) tuples until patience runs out or Ctrl-C.

    fill : term -> state, substitutes sketches into holes and simplifies
    validate : state -> bool, must be sound, may be incomplete
    language : Language proto
    free_vars : list(Expression)
    '''
    assert callable(fill), fill
    assert callable(validate), validate
    assert isinstance(language, Language), language
    assert patience > 0, patience
    free_vars = sorted(set(free_vars))
    complexity = ComplexityEvaluator(language, free_vars)
    fill_holes = NaiveHoleFiller(language, free_vars)
    sketches = iter_sketches(complexity, fill_holes)
    sketches = filter_normal_sketches(sketches)
    lazy_valid_sketches = lazy_iter_valid_sketches(fill, validate, sketches)
    for term, sketch in impatient_iterator(lazy_valid_sketches, patience):
        yield complexity(term), term, sketch  # suitable for sort()


@memoize_args
def _db_simplify_expr(db, expr):
    string = db.simplify([expr.polish])[0]
    expr = parse_string_to_expr(string)
    expr = unguard_vars(expr)
    return expr


@inputs(object, Expression)
def simplify_filling(db, term):
    term = simplify_expr(term)
    term = _db_simplify_expr(db, term)
    return term


def is_def(fact):
    return fact.name == 'EQUAL' and fact.args[0].is_var()


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


def simplify_defs(facts):
    '''
    Substitute all facts of form 'EQUAL var closed_term' into remaining facts.
    In case of multiple equivalent definitions,
    all combinations of substitutions will be added.
    This generally reduces the number of free variables.
    '''
    facts = set(desugar_expr(f) for f in facts)
    defs = {}
    extract_defs_from_facts(facts, defs)
    changed = True
    while changed:
        changed = False
        for var, bodies in defs.items():
            if any(v in defs for b in bodies for v in b.vars):
                continue  # avoid cycles
            del defs[var]
            substitute_bodies(facts, var, bodies)
            for var2, bodies2 in defs.iteritems():
                substitute_bodies(bodies2, var, bodies)
            extract_defs_from_facts(facts, defs)
            changed = True
    for var, bodies in defs.iteritems():
        facts.add(EQUAL(var, b) for b in bodies)
    return facts


def simplify_facts(db, facts):
    assert isinstance(facts, list), facts
    assert all(isinstance(f, Expression) for f in facts), facts
    facts = set(simplify_expr(f) for f in facts)
    facts = simplify_defs(facts)
    strings = db.simplify([f.polish for f in facts])
    facts = set(parse_string_to_expr(s) for s in strings)
    facts = map(unguard_vars, facts)
    return facts


class FactsValidator(object):
    def __init__(self, db, facts, var, verbose=False):
        assert isinstance(facts, list), facts
        assert all(isinstance(f, Expression) for f in facts), facts
        assert isinstance(var, Expression), var
        assert var.is_var(), var
        facts = simplify_facts(db, facts)
        self._db = db
        self._facts = facts
        self._var = var
        self._verbose = verbose
        free_vars = union(f.vars for f in facts)
        assert var in free_vars, 'facts do not depend on {}'.format(var)
        self._free_vars = sorted(free_vars - set([var]))

    def free_vars(self):
        return self._free_vars[:]

    def fill(self, filling):
        return simplify_filling(self._db, filling)

    def validate(self, filling):
        if self._verbose:
            print 'Filling:', filling
        facts = [f.substitute(self._var, filling) for f in self._facts]
        facts = simplify_facts(self._db, facts)
        truthy = I  # facts proven true
        falsey = BOT  # facts proven false
        unknown_facts = []
        for fact in facts:
            if fact == falsey:
                return False
            if fact == truthy:
                continue
            unknown_facts.append(fact)
        facts = unknown_facts
        strings = [f.polish for f in facts]
        return self._db.validate_facts(strings)


@inputs(Expression)
def is_complete(expr):
    return expr is not HOLE and all(is_complete(arg) for arg in expr.args)
