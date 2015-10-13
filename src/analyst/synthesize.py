import heapq

PATIENCE_LIMIT = 10000


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


def iter_sketches(priority, start, get_next):
    '''
    priority : term -> float
    start : term, e.g., HOLE
    get_next : term -> list(term), must increase priority, decrease validity
    '''
    assert callable(priority), priority
    assert callable(get_next), get_next
    queue = UniquePriorityQueue(priority)
    queue.push(start)
    while True:
        sketch = queue.pop()
        steps = get_next(sketch)
        assert isinstance(steps, list), steps
        for step in steps:
            queue.push(step)
        yield sketch, steps


def lazy_iter_valid_sketches(context, validate, sketches):
    '''
    This yields a mixture of (term, sketch) pairs and Nones;
    consumers should filter out Nones.
    Since satisfiability is undecidable, consumers must decide when to give up.

    context : term -> term, substitutes sketches into holes and simplifies
    validate : term -> bool, must be sound, may be incomplete
    sketches : stream(term)
    '''
    invalid_sketches = set()
    invalid_terms = set()
    valid_terms = set()
    for sketch, steps in sketches:
        if sketch in invalid_sketches:
            invalid_sketches.update(steps)  # propagate
            yield
            continue

        # filter out previously-seen terms
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


def impatient_iterator(lazy_iterator, patience_limit=PATIENCE_LIMIT):
    patience = patience_limit
    for value_or_none in lazy_iterator:
        if value_or_none is not None:
            patience = patience_limit
            yield value_or_none
        else:
            patience -= 1
            if patience == 0:
                raise StopIteration


def iter_valid_sketches(
        context,
        validate,
        complexity,
        sketch_start,
        sketch_next,
        patience_limit=PATIENCE_LIMIT):
    sketches = iter_sketches(complexity, sketch_start, sketch_next)
    lazy_valid_sketches = lazy_iter_valid_sketches(context, validate, sketches)
    return impatient_iterator(lazy_valid_sketches, patience_limit)
