import os
import pomagma.util


def TODO(message):
    raise NotImplementedError('TODO {}'.format(message))


DEFAULT_STORE = os.path.join(pomagma.util.SRC, 'corpus', 'store.dump')


example_object = {
    '_id': 'asfgvg1tr457et46979yujkm',
    'name': 'div',      # or None for
    'code': 'APP V K',  # compiled code
    'args': [],         # names this object references, list w/o repeats
    'version': 123456,  # TODO deal with version conflicts
}


class IdGenerator(object):
    def __init__(self):
        self._next = 0

    def __call__(self):
        self._next += 1
        return self._next


class LineStore(object):
    '''
    Database for lines of code.
    '''
    def __init__(self):
        self._objects = {}  # oid -> object
        self._defs = {}     # name -> oid
        self._refs = {}     # name -> (set oid)
        self._new_id = IdGenerator()

    def load(self, oid):
        return self._objects.get(oid)

    def find_def(self, name):
        try:
            oid = self._defs[name]
            return self.load(oid)
        except KeyError:
            return None

    def find_refs(self, name):
        for obj in self._refs[name]:
            yield obj

    def find_all(self):
        # this is the only way to get unreferenced objects
        for obj in self._objects.itervalues():
            yield obj

    def create(self, obj):
        obj = dict(obj)
        obj['args'] = list(obj['args'])
        assert '_id' not in obj
        oid = self._new_id()
        obj['_id'] = oid
        self._objects[oid] = obj
        name = obj['name']
        if name is not None:
            assert name not in self._defs
            self._defs[name] = obj
        for arg in obj['args']:
            self._refs[arg].add(oid)
        return oid

    def update(self, obj):
        TODO('replace old object with new')

    def remove(self, oid):
        obj = self._objects.pop(oid)
        for arg in obj['args']:
            self._refs[arg].remove(oid)
        name = obj['name']
        if name is not None:
            del self._defs[name]
            refs = self._refs.pop(name)
            for obj in refs:
                TODO('replace name with hole?')

    def dump(db, filename):
        TODO('adapt from module store method')

    def restore(db, filename):
        TODO('adapt from module load method')


def merge_dumps(version1, version2, merged):
    '''
    Merge two database dumps for git.
    '''
    raise NotImplementedError('TODO')
