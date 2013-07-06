import re
import os
import pomagma.util


CORPUS = os.path.join(pomagma.util.SRC, 'corpus')
IDENTIFIER_RE = re.compile(r'^[^\d\W]\w*$')
FILE_RE = re.compile(r'^[^\d\W]\w*\.defs$')
EXT = '.defs'


def assert_identifier(name):
    if not IDENTIFIER_RE.match(name):
        raise ValueError('bad identifier: {}'.format(name))


def assert_defs(defs):
    if not isinstance(defs, dict):
        raise ValueError('bad definitions: {}'.format(defs))
    for name in defs:
        assert_identifier(name)


def _get_module_path(module_name):
    parts = module_name.split('.')
    for part in parts:
        assert_identifier(part)
    return os.path.join(CORPUS, * parts)


def _list_modules_here():
    modules = []
    dirs = []
    for f in os.path.listdir('.'):
        if IDENTIFIER_RE.match(f) and os.path.isdir(f):
            dirs.append(f)
        elif FILE_RE.match(f) and not os.path.isdir(f):
            modules.append(f.split('.')[0])
    modules.sort()
    dirs.sort()
    for d in dirs:
        with pomagma.util.chdir(d):
            modules += _list_modules_here()
    return modules


def list_modules(prefix=''):
    '''
    Return a flat sorted list of all modules with given prefix.
    '''
    path = _get_module_path(prefix)
    with pomagma.util.chdir(path):
        modules = _list_modules_here()
    if prefix:
        parts = prefix.split('.')
    modules = ['.'.join(parts + [m]) for m in modules]
    return modules


def load_module(module_name):
    '''
    Atomically load module.
    '''
    path = _get_module_path(module_name) + EXT
    if os.path.exists(path):
        with open(path) as file:
            lines = filter(bool, (line.strip() for line in file))
    else:
        lines = []
    defs = {}
    for line in lines:
        let, name, ugly = line.split(maxsplit=2)
        assert let == 'LET', 'bad line: {}'.format(line)
        assert_identifier(name)
        defs[name] = ugly
    return defs


def store_module(module_name, defs):
    '''
    Atomically store module.
    '''
    assert_defs(defs)
    text = '\n'.join(
        'LET {} {}'.format(name, defs[name])
        for name in sorted(defs.iterkeys())
    )
    path = _get_module_path(module_name) + EXT
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    tempfile = os.path.join(dirname, '{}.temp'.format(os.getpid()))
    with open(tempfile, 'w') as file:
        file.write(text)
    os.rename(tempfile, path)


def sort_module(defs):
    '''
    Return a heuristically sorted list of definitions.

    TODO use approximately topologically-sorted order.
    (R1) "A Technique for Drawing Directed Graphs" -Gansner et al
      http://www.graphviz.org/Documentation/TSE93.pdf
    (R2) "Combinatorial Algorithms for Feedback Problems in Directed Graphs"
      -Demetrescu and Finocchi
      http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1.9435
    '''
    assert_defs(defs)
    sorted_defs = defs.items()
    sorted_defs.sort(key=lambda(name, ugly): (len(ugly), name))
    return sorted_defs
