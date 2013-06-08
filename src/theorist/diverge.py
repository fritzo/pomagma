import parsable
parsable = parsable.Parsable()


I, K, B, C, W, S, Y, TOP = 'I', 'K', 'B', 'C', 'W', 'S', 'Y', 'TOP'


class Converged(Exception):
    pass


def diverge_step(term):
    head = term[0]
    argv = term[1:]
    argc = len(argv)
    if head == I:
        if argc == 0:
            return [TOP]
        else:
            return argv[0] + argv[1:]
    elif head == K:
        if argc == 0:
            return [TOP]
        else:
            return argv[0] + argv[2:]
    elif head == B:
        if argc == 0:
            return [TOP]
        elif argc == 1:
            return argv[0]
        elif argc == 2:
            return argv[0] + [argv[1] + [[TOP]]] + argv[3:]
        else:
            return argv[0] + [argv[1] + [argv[2]]] + argv[3:]
    elif head == C:
        if argc == 0:
            return [TOP]
        elif argc == 1:
            return argv[0]
        elif argc == 2:
            return argv[0] + [[TOP], argv[1]]
        else:
            return argv[0] + [argv[2], argv[1]] + argv[3:]
    elif head == W:
        if argc == 0:
            return [TOP]
        elif argc == 1:
            return argv[0] + [[TOP], [TOP]]
        else:
            return argv[0] + [argv[1], argv[1]] + argv[2:]
    elif head == S:
        if argc == 0:
            return [TOP]
        elif argc == 1:
            return argv[0] + [[TOP], [TOP]]
        elif argc == 2:
            return argv[0] + [[TOP], argv[1] + [[TOP]]]
        else:
            return argv[0] + [argv[2], argv[1] + [argv[2]]] + argv[3:]
    elif head == Y:
        if argc == 0:
            return [TOP]
        else:
            return argv[0] + [[Y, argv[0]]] + argv[1:]
    elif head == TOP:
        raise Converged()


def try_converge(term, steps):
    for _ in xrange(steps):
        term = diverge_step(term)


def iter_terms(atoms, max_atom_count):
    assert max_atom_count > 0
    for atom_count in xrange(1, 1 + max_atom_count):
        if atom_count == 1:
            for atom in atoms:
                yield [atom]
        else:
            for lhs_count in xrange(1, atom_count):
                rhs_count = atom_count - lhs_count
                for lhs in iter_terms(atoms, lhs_count):
                    for rhs in iter_terms(atoms, rhs_count):
                        yield lhs + [rhs]
    raise StopIteration()


@parsable.command
def print_terms(atoms, max_atom_count=3):
    '''
    Print all terms up to some max atom count.
    atoms is a comma-delimited list of atoms.
    '''
    atoms = atoms.split(',')
    for term in iter_terms(atoms, max_atom_count):
        print term


@parsable.command
def count_terms(max_count=8):
    '''
    Count all terms up to some max atom count.
    '''
    atom_counts = range(1, 1 + max_count)
    max_counts = range(1, 1 + max_count)
    count = lambda a, m: sum(1 for term in iter_terms(range(a), m))
    print '\t' * (max_count / 2) + '|atoms|'
    print '\t'.join(['|term|'] + [str(a) for a in atom_counts])
    print '-' * 8 * (1 + max_count)
    for m in max_counts:
        counts = [count(a, m) for a in atom_counts if a + m <= max_count + 1]
        print '\t'.join(map(str, [m] + counts))


@parsable.command
def may_diverge(atoms='I,K,B,C,W,S,Y', max_atom_count=4, max_steps=20):
    '''
    Print terms that have not been found to converge.
    '''
    atoms = atoms.split(',')
    for term in iter_terms(atoms, max_atom_count):
        try:
            try_converge(term, max_steps)
            print term
        except Converged:
            pass


if __name__ == '__main__':
    parsable.dispatch()
