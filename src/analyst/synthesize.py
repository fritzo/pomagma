import heapq
import math
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_1
from pomagma.language.util import Language
from pomagma.language.util import language_to_dict

PATIENCE = 10000
HOLE = Expression.make('HOLE')
VAR = Expression_1('VAR')


class ComplexityEvaluator(object):
    def __init__(self, language, var_names=[]):
        assert isinstance(language, Language), language
        self._signature = {t.name: t.weight for t in language.terms}
        var_count = len(var_names)
        self._var_cost = math.log(var_count) if var_count else float('inf')

    def __call__(self, term):
        assert isinstance(term, Expression)
        if term == HOLE:
            return 0.0
        elif term.is_var():
            return self._var_cost
        else:
            result = self._signature.get(term.name, 0.0)  # ignore unknowns
            for arg in term.args:
                result += self(arg)
            return result


class NaiveHoleFiller(object):
    'A more intelligent hole filler would only enumerate normal forms'
    def __init__(self, language, var_names):
        assert isinstance(language, Language), language
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
        for name in sorted(var_names):
            fillings.append(Expression.make(name))
        self._fillings = fillings

    def __call__(self, term):
        if term == HOLE:
            for f in self._fillings:
                yield f
        elif len(term.args) == 1:
            name = term.name
            key, = term.args
            for f in self(key):
                yield Expression.make(name, f)
        elif len(term.args) == 2:
            name = term.name
            lhs, rhs = term.args
            for f in self(lhs):
                yield Expression.make(name, f, rhs)
            for f in self(rhs):
                yield Expression.make(name, lhs, f)


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
        steps = list(fill_holes(sketch))
        for step in steps:
            queue.push(step)
        yield sketch, steps


def lazy_iter_valid_sketches(context, validate, sketches):
    '''
    Yield (term, sketch) pairs and Nones; consumers should filter out Nones.
    Since satisfiability is undecidable, consumers must decide when to give up.

    context : term -> term, substitutes sketches into holes and simplifies
    validate : term -> bool, must be sound, may be incomplete
    sketches : stream(term)
    '''
    assert callable(context), context
    assert callable(validate), validate
    invalid_sketches = set()
    invalid_terms = set()
    valid_terms = set()
    for sketch, steps in sketches:
        if sketch in invalid_sketches:
            invalid_sketches.update(steps)  # propagate
            yield
            continue
        term = context(sketch)
        if term in valid_terms:
            yield
            continue
        if term in invalid_terms or not validate(term):
            invalid_terms.add(term)
            invalid_sketches.update(steps)  # propagate
            yield
            continue

        valid_terms.add(term)
        yield term, sketch


def impatient_iterator(lazy_iterator, patience=PATIENCE):
    assert patience > 0, patience
    patience_remaining = patience
    for value_or_none in lazy_iterator:
        if value_or_none is not None:
            patience_remaining = patience
            yield value_or_none
        else:
            patience_remaining -= 1
            if patience_remaining == 0:
                raise StopIteration


# this ties everything together
def iter_valid_sketches(context, validate, language, patience=PATIENCE):
    assert callable(context), context
    assert callable(validate), validate
    assert isinstance(language, Language), language
    assert patience > 0, patience
    var_names = sorted(v.name for v in context(HOLE).vars)
    complexity = ComplexityEvaluator(language, var_names)
    fill_holes = NaiveHoleFiller(language, var_names)
    sketches = iter_sketches(complexity, fill_holes)
    lazy_valid_sketches = lazy_iter_valid_sketches(context, validate, sketches)
    for term, sketch in impatient_iterator(lazy_valid_sketches, patience):
        yield complexity(term), term, sketch  # suitable for sort()
