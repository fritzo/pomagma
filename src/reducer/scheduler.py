from pomagma.util import TODO

# These should all be memoized.
DEFAULT_STRATEGY = {
    'get_next': lambda v: TODO('generate a tuple of next vertices'),
    'get_below': lambda v: TODO('generate the set of vertices below v'),
    'priority': lambda v: TODO('compute vertex priority (lowest runs first)'),
}


class Scheduler(object):

    def __init__(self, start_task, strategy=None):
        self._strategy = DEFAULT_STRATEGY if strategy is None else strategy
        self._seen = set()
        self._pending = set()
        self._normal = set()
        self._reduced = None
        self._schedule(start_task)

    def _schedule(self, task):
        assert task not in self._seen
        self._seen.add(task)
        self._pending.add(task)
        get_next = self._strategy['get_next']
        for dominated in self._strategy['get_below'](task):
            if dominated in self._pending:
                self._pending.remove(dominated)
            self._seen.add(dominated)
            if not get_next(dominated):
                self._normal.add(dominated)

    def try_work(self):
        """Does work; returns true until work is done; then returns false."""
        if not self._pending:
            return False
        task = min(self._pending, key=self._strategy['priority'])
        self._pending.remove(task)
        next_tasks = self._strategy['get_next'](task)
        if next_tasks:
            for t in next_tasks:
                if t not in self._seen:
                    self._schedule(t)
        else:
            self._normal.add(task)
        return True

    @property
    def result(self):
        if self._pending:
            raise ValueError('Work is not done; call .try_work() first')
        if self._reduced is None:
            # Winnow down self._normal to remove dominated tasks.
            reduced = set(self._normal)
            get_below = self._strategy['get_below']
            for x in self._normal:
                for y in self._normal:
                    if x in get_below(y):
                        assert y not in get_below(x), \
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
