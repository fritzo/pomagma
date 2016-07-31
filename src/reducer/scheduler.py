from pomagma.util import TODO

# These should all be memoized.
DEFAULT_STRATEGY = {
    'get_next': lambda v: TODO('generate a tuple of next vertices'),
    'is_below': lambda u, v: TODO('decide whether u is strictly below v'),
    'priority': lambda v: TODO('compute vertex priority (lowest runs first)'),
}


class Scheduler(object):

    def __init__(self, start_task, strategy=None):
        self._strategy = DEFAULT_STRATEGY if strategy is None else strategy
        self._seen = set()
        self._pending = set()
        self._reduced = None
        self._schedule(start_task)

    def _schedule(self, task):
        if task in self._seen:
            return
        self._seen.add(task)
        self._pending.add(task)
        is_below = self._strategy['is_below']
        for dominated in self._pending:
            if is_below(dominated, task):
                self._pending.remove(dominated)
            self._seen.add(dominated)

    def try_work(self):
        """Does work; returns true until work is done; then returns false."""
        if not self._pending:
            return False
        task = min(self._pending, key=self._strategy['priority'])
        self._pending.remove(task)
        for t in self._strategy['get_next'](task):
            self._schedule(t)
        return True

    @property
    def result(self):
        if self._pending:
            raise ValueError('Work is not done; call .try_work() first')
        if self._reduced is None:
            get_next = self._strategy['get_next']
            is_below = self._strategy['is_below']
            normal = [t for t in self._seen if not get_next(t)]
            # Winnow down normal to remove dominated tasks.
            reduced = set(normal)
            for x in normal:
                for y in normal:
                    if is_below(x, y):
                        assert not is_below(y, x), \
                            'failed antisymmetry for {}, {}'.format(x, y)
                        reduced.remove(x)
                        break
            self._reduced = frozenset(reduced)
        return self._reduced


def execute(task, strategy=None):
    scheduler = Scheduler(task)
    while scheduler.try_work():
        pass
    return scheduler.result
