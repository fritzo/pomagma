import heapq


class UniquePriorityQueue(object):
    '''Duplicates may not be pushed. The Lowest-priority item is popped.'''
    def __init__(self):
        self._to_pop = []
        self._pushed = set()

    def __nonzero__(self):
        return bool(self._to_pop)

    def __len__(self):
        return len(self._to_pop)

    def __contains__(self, item):
        return self._pushed.contains(item)

    def push(self, item, priority):
        assert item not in self._pushed, 'cannot push item twice'
        self._pushed.add(item)
        heapq.heappush(self._to_pop, (priority, item))

    def pop(self):
        assert self._to_pop, 'cannot pop from empty queue'
        return heapq.heappop(self._to_pop)[1]


class IterRefinements(object):
    def __init__(
            self,
            context,
            validate,
            complexity,
            refine_start,
            refine_step,
            lookahead=100):
        '''
        context : term -> term, substitutes fillings into holes and simplifies
        validate : term -> bool, must be sound, may be incomplete
        complexity : term -> float
        refine_start : term, e.g., HOLE
        refine_step : term -> list(term),
            must increase complexity, decrease validity
        lookahead is a heuristic parameter
        '''
        assert callable(context), context
        assert callable(validate), validate
        assert callable(complexity), complexity
        assert callable(refine_step), refine_step
        assert isinstance(lookahead, int) and lookahead > 0, lookahead
        self._context = context
        self._validate = validate
        self._complexity = complexity
        self._refine_step = refine_step
        self._lookahead = lookahead
        self._filling_queue = UniquePriorityQueue()
        self._substitution_queue = UniquePriorityQueue()
        self._filling_queue.push(refine_start)

    def __iter__(self):
        return self

    def next(self):
        while len(self._substitution_queue) < self._lookahead:
            if not self._try_find_substitutions():
                break
        if not self._substitution_queue.pop:
            raise StopIteration()
        return self._substitution_queue.pop()

    def _try_find_substitutions(self):
        '''Returns true if any progress is made.'''
        if not self._filling_queue:
            return False
        filling = self._filling_queue.pop()
        substitution = self._context(filling)
        if substitution in self._substitution_queue:
            return
        if not self._validate(substitution):
            return
        priority = self._complexity(substitution)
        self._substitution_queue.push(substitution, priority)
        for refinement in self._refine_step(filling):
            if refinement not in self._filling_queue:
                priority = self._complexity(refinement)
                self._filling_queue.push(refinement)
        return True
