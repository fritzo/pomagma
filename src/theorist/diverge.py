from itertools import izip
import parsable
parsable = parsable.Parsable()
import pomagma.util


# ----------------------------------------------------------------------------
# Term enumeration


BOT, TOP = 'BOT', 'TOP'
I, K, B, C, W, S, Y = 'I', 'K', 'B', 'C', 'W', 'S', 'Y'
J, R, U, V, P, A = 'J', 'R', 'U', 'V', 'P', 'A'


def iter_terms(atoms, max_atom_count):
    assert max_atom_count > 0
    for atom_count in xrange(1, 1 + max_atom_count):
        if atom_count == 1:
            for atom in atoms:
                yield (atom,)
        else:
            for lhs_count in xrange(1, atom_count):
                rhs_count = atom_count - lhs_count
                for lhs in iter_terms(atoms, lhs_count):
                    for rhs in iter_terms(atoms, rhs_count):
                        yield lhs + (rhs,)
    raise StopIteration()


# ----------------------------------------------------------------------------
# Convergence testing


class Converged(Exception):
    pass


class Diverged(Exception):
    pass


class Unknown(Exception):
    pass


def converge_step(term):
    head = term[0]
    assert isinstance(head, str), 'bad head: {}'.format(head)
    argv = term[1:]
    argc = len(argv)
    if head == TOP:
        raise Converged()
    elif head == BOT:
        raise Diverged()
    elif head == I:
        if argc == 0:
            return (TOP,)
        else:
            return argv[0] + argv[1:]
    elif head == K:
        if argc == 0:
            return (TOP,)
        else:
            return argv[0] + argv[2:]
    elif head == B:
        if argc == 0:
            return (TOP,)
        elif argc == 1:
            return argv[0]
        elif argc == 2:
            return argv[0] + (argv[1] + ((TOP,),),) + argv[3:]
        else:
            return argv[0] + (argv[1] + (argv[2],),) + argv[3:]
    elif head == C:
        if argc == 0:
            return (TOP,)
        elif argc == 1:
            return argv[0]
        elif argc == 2:
            return argv[0] + ((TOP,), argv[1],)
        else:
            return argv[0] + (argv[2], argv[1],) + argv[3:]
    elif head == W:
        if argc == 0:
            return (TOP,)
        elif argc == 1:
            return argv[0] + ((TOP,), (TOP,),)
        else:
            return argv[0] + (argv[1], argv[1],) + argv[2:]
    elif head == S:
        if argc == 0:
            return (TOP,)
        elif argc == 1:
            return argv[0] + ((TOP,), (TOP,),)
        elif argc == 2:
            return argv[0] + ((TOP,), argv[1] + ((TOP,),),)
        else:
            return argv[0] + (argv[2], argv[1] + (argv[2],),) + argv[3:]
    elif head == Y:
        if argc == 0:
            return (TOP,)
        else:
            return argv[0] + ((Y, argv[0],),) + argv[1:]
    elif head == J:
        if argc <= 1:
            return (TOP,)
        elif argc == 2:
            return (J, converge_step(argv[1]), argv[0],)
        else:
            return (J, argv[0] + argv[2:], argv[1] + argv[2:],)
    elif head == U:
        if argc == 0:
            return (TOP,)
        else:
            f = argv[0]
            return (J, f, (B, f, (U, f,),),) + argv[1:]
    elif head == V:
        if argc == 0:
            return (TOP,)
        else:
            f = argv[0]
            return (J, (I,), (B, f, (U, f,),),) + argv[1:]
    elif head == P:
        if argc <= 1:
            return (TOP,)
        else:
            f = argv[0]
            g = argv[1]
            return (V, (J, f, g,),) + argv[2:]
    elif head in [R, A]:
        raise Unknown()
    else:
        raise ValueError('unrecognized atom: {}'.format(head))


def trivially_less(lhs, rhs):
    return lhs == (BOT,) or lhs == rhs or rhs == (TOP,)


def converge_less(lhs, rhs):
    if lhs == rhs:
        return True
    if len(rhs) < len(lhs):
        rhs = rhs + ((TOP,),) * (len(lhs) - len(rhs))
    if len(lhs) < len(rhs):
        lhs = lhs + ((TOP,),) * (len(rhs) - len(lhs))
    lhs_head, lhs_args = lhs[:1], lhs[1:]
    rhs_head, rhs_args = rhs[:1], rhs[1:]
    if not trivially_less(lhs_head, rhs_head):
        return False
    for lhs_arg, rhs_arg in izip(lhs_args, rhs_args):
        if not trivially_less(lhs_arg, rhs_arg):
            return False
    return True


def try_converge(term, steps):
    '''
    If a term 'DIV x' head reduces to a term less than or equal to itself,
    then it diverges.
    '''
    seen = set([term])
    for _ in xrange(steps):
        try:
            term = converge_step(term)
        except Unknown:
            return
        for other in seen:
            if converge_less(term, other):
                raise Diverged
        seen.add(term)


# ----------------------------------------------------------------------------
# Parsing


def parse_tokens_unsafe(tokens):
    head = tokens.pop()
    if head == 'APP':
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return lhs + (rhs,)
    elif head == 'COMP':
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (B, lhs, rhs,)
    elif head == 'JOIN':
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (J, lhs, rhs,)
    elif head == 'RAND':
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (R, lhs, rhs,)
    elif head == 'CI':
        return (C, (I,),)
    elif head == 'CB':
        return (C, (B,),)
    else:
        return (head,)


def parse_tokens(tokens):
    term = parse_tokens_unsafe(tokens)
    assert not tokens, 'unexpected tokens: {}'.format(' '.join(tokens))
    return term


def parse_term(string):
    tokens = string.split()
    tokens.reverse()
    return parse_tokens(tokens)


def add_tokens(tokens, term):
    head, args = term[0], term[1:]
    tokens += ['APP'] * len(args)
    tokens.append(head)
    for arg in args:
        add_tokens(tokens, arg)


def print_term(term):
    tokens = []
    add_tokens(tokens, term)
    return ' '.join(tokens)


def stripped_lines(file_in):
    with open(file_in) as f:
        for line in f:
            line = line.split('#')[0].strip()
            if line:
                yield line
    raise StopIteration()


# ----------------------------------------------------------------------------
# Main


def try_prove_diverge(
        conjectures_in,
        conjectures_out,
        theorems_out,
        max_steps=20,
        log_file=None,
        log_level=0):
    assert conjectures_in != theorems_out
    assert conjectures_out != theorems_out

    def log_print(message):
        if log_file:
            pomagma.util.log_print(message, log_file)
        else:
            print message

    lines = list(stripped_lines(conjectures_in))
    log_print('Trying to prove {} conjectures'.format(len(lines)))

    conjecture_count = 0
    diverge_count = 0
    converge_count = 0
    with open(conjectures_out, 'w') as conjectures:
        conjectures.write('# divergence conjectures filtered by pomagma\n')
        with open(theorems_out, 'a') as theorems:

            def write_theorem(theorem):
                if log_level >= pomagma.util.LOG_LEVEL_DEBUG:
                    log_print('proved {}'.format(theorem))
                if diverge_count + converge_count == 0:
                    theorems.write('# divergence theorems proved by pomagma\n')
                theorems.write(theorem)
                theorems.write('\n')

            for line in lines:
                assert line.startswith('EQUAL BOT ')
                term_string = line[len('EQUAL BOT '):]
                term = parse_term(term_string)
                try:
                    try_converge(term, max_steps)
                    conjectures.write(line)
                    conjectures.write('\n')
                    conjecture_count += 1
                except Diverged:
                    theorem = 'EQUAL BOT {}'.format(term_string)
                    write_theorem(theorem)
                    diverge_count += 1
                except Converged:
                    theorem = 'NLESS {} BOT'.format(term_string)
                    write_theorem(theorem)
                    converge_count += 1
    if log_level >= pomagma.util.LOG_LEVEL_INFO:
        log_print('Proved {} diverge theorems'.format(diverge_count))
        log_print('Proved {} converge theorems'.format(converge_count))
        log_print('Failed to prove {} conjectures'.format(conjecture_count))
    theorem_count = diverge_count + converge_count
    return theorem_count


# ----------------------------------------------------------------------------
# Commands


@parsable.command
def print_terms(atoms='x,y', max_atom_count=3):
    '''
    Print all terms up to some max atom count.
    atoms is a comma-delimited list of atoms.
    '''
    atoms = atoms.split(',')
    for term in iter_terms(atoms, max_atom_count):
        print print_term(term)


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
    Print terms that have not been proven to converge.
    '''
    atoms = atoms.split(',')
    for term in iter_terms(atoms, max_atom_count):
        try:
            try_converge(term, max_steps)
            print term
        except Diverged:
            print term
        except Converged:
            pass


@parsable.command
def must_diverge(atoms='I,K,B,C,W,S,Y', max_atom_count=4, max_steps=20):
    '''
    Print terms that have been proven to diverge.
    '''
    atoms = atoms.split(',')
    for term in iter_terms(atoms, max_atom_count):
        try:
            try_converge(term, max_steps)
        except Converged:
            pass
        except Diverged:
            print term


if __name__ == '__main__':
    parsable.dispatch()
