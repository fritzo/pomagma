import parsable

import pomagma.util

parsable = parsable.Parsable()


################################################################
# Term enumeration


BOT, TOP = "BOT", "TOP"
I, K, F, B, C, W, S, Y = "I", "K", "F", "B", "C", "W", "S", "Y"
J, R, U, V, P = "J", "R", "U", "V", "P"
UNKNOWNS = [
    "A",
    "SECTION",
    "RETRACT",
    "DIV",
    "UNIT",
    "SEMI",
    "BOOL",
    "BOOOL",
    "MAYBE",
    "SOME",
    "NUM",
    "SUCC",
    "PRED",
]


def iter_terms(atoms, max_atom_count):
    assert max_atom_count > 0
    for atom_count in range(1, 1 + max_atom_count):
        if atom_count == 1:
            for atom in atoms:
                yield (atom,)
        else:
            for lhs_count in range(1, atom_count):
                rhs_count = atom_count - lhs_count
                for lhs in iter_terms(atoms, lhs_count):
                    for rhs in iter_terms(atoms, rhs_count):
                        yield (*lhs, rhs)


################################################################
# Convergence testing


class Converged(Exception):
    pass


class Diverged(Exception):
    pass


class Unknown(Exception):
    pass


def converge_step(term):
    head = term[0]
    assert isinstance(head, str), f"bad head: {head}"
    argv = term[1:]
    argc = len(argv)
    if head == TOP:
        raise Converged
    if head == BOT:
        raise Diverged
    if head == I:
        if argc == 0:
            return (TOP,)
        return argv[0] + argv[1:]
    if head == K:
        if argc == 0:
            return (TOP,)
        return argv[0] + argv[2:]
    if head == F:
        if argc == 0:
            return (TOP,)
        if argc == 1:
            return (TOP,)
        return argv[1] + argv[2:]
    if head == B:
        if argc == 0:
            return (TOP,)
        if argc == 1:
            return argv[0]
        if argc == 2:
            return argv[0] + (argv[1] + ((TOP,),),) + argv[3:]
        return argv[0] + (argv[1] + (argv[2],),) + argv[3:]
    if head == C:
        if argc == 0:
            return (TOP,)
        if argc == 1:
            return argv[0]
        if argc == 2:
            return argv[0] + (
                (TOP,),
                argv[1],
            )
        return (
            argv[0]
            + (
                argv[2],
                argv[1],
            )
            + argv[3:]
        )
    if head == W:
        if argc == 0:
            return (TOP,)
        if argc == 1:
            return argv[0] + (
                (TOP,),
                (TOP,),
            )
        return (
            argv[0]
            + (
                argv[1],
                argv[1],
            )
            + argv[2:]
        )
    if head == S:
        if argc == 0:
            return (TOP,)
        if argc == 1:
            return argv[0] + (
                (TOP,),
                (TOP,),
            )
        if argc == 2:
            return argv[0] + (
                (TOP,),
                argv[1] + ((TOP,),),
            )
        return (
            argv[0]
            + (
                argv[2],
                argv[1] + (argv[2],),
            )
            + argv[3:]
        )
    if head == Y:
        if argc == 0:
            return (TOP,)
        return (
            argv[0]
            + (
                (
                    Y,
                    argv[0],
                ),
            )
            + argv[1:]
        )
    if head == J:
        if argc <= 1:
            return (TOP,)
        if argc == 2:
            return (
                J,
                converge_step(argv[1]),
                argv[0],
            )
        return (
            J,
            argv[0] + argv[2:],
            argv[1] + argv[2:],
        )
    if head == U:
        if argc == 0:
            return (TOP,)
        f = argv[0]
        return (
            J,
            f,
            (
                B,
                f,
                (
                    U,
                    f,
                ),
            ),
        ) + argv[1:]
    if head == V:
        if argc == 0:
            return (TOP,)
        f = argv[0]
        return (
            J,
            (I,),
            (
                B,
                f,
                (
                    U,
                    f,
                ),
            ),
        ) + argv[1:]
    if head == P:
        if argc <= 1:
            return (TOP,)
        f = argv[0]
        g = argv[1]
        return (
            V,
            (
                J,
                f,
                g,
            ),
        ) + argv[2:]
    if head in [R]:
        raise Unknown
    if head in UNKNOWNS:
        raise Unknown
    print(f"WARNING unrecognized atom: {head}")
    raise Unknown


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
    for lhs_arg, rhs_arg in zip(lhs_args, rhs_args):
        if not trivially_less(lhs_arg, rhs_arg):
            return False
    return True


def try_converge(term, steps):
    """If a term 'DIV x' head reduces to a term less than or equal to itself,
    then it diverges."""
    seen = {term}
    for _ in range(steps):
        try:
            term = converge_step(term)
        except Unknown:
            return
        for other in seen:
            if converge_less(term, other):
                raise Diverged
        seen.add(term)


################################################################
# Parsing


def parse_tokens_unsafe(tokens):
    head = tokens.pop()
    if head == "APP":
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (*lhs, rhs)
    if head == "COMP":
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (
            B,
            lhs,
            rhs,
        )
    if head == "JOIN":
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (
            J,
            lhs,
            rhs,
        )
    if head == "RAND":
        lhs = parse_tokens_unsafe(tokens)
        rhs = parse_tokens_unsafe(tokens)
        return (
            R,
            lhs,
            rhs,
        )
    if head == "CI":
        return (
            C,
            (I,),
        )
    if head == "CB":
        return (
            C,
            (B,),
        )
    return (head,)


def parse_tokens(tokens):
    term = parse_tokens_unsafe(tokens)
    assert not tokens, "unexpected tokens: {}".format(" ".join(tokens))
    return term


def parse_term(string):
    tokens = string.split()
    tokens.reverse()
    return parse_tokens(tokens)


def add_tokens(tokens, term):
    head, args = term[0], term[1:]
    tokens += ["APP"] * len(args)
    tokens.append(head)
    for arg in args:
        add_tokens(tokens, arg)


def print_term(term):
    tokens = []
    add_tokens(tokens, term)
    return " ".join(tokens)


def stripped_lines(file_in):
    with open(file_in) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                yield line


################################################################
# Main


def try_prove_diverge(
    conjectures_in,
    conjectures_out,
    theorems_out,
    max_steps=20,
    log_file=None,
    log_level=0,
    **unused,
):
    assert conjectures_in != theorems_out
    assert conjectures_out != theorems_out

    def log_print(message):
        if log_file:
            pomagma.util.log_print(message, log_file)
        else:
            print(message)

    lines = list(stripped_lines(conjectures_in))
    log_print(f"Trying to prove {len(lines)} conjectures")

    conjecture_count = 0
    diverge_count = 0
    converge_count = 0
    with open(conjectures_out, "w") as conjectures:
        conjectures.write("# divergence conjectures filtered by pomagma\n")
        with open(theorems_out, "a") as theorems:

            def write_theorem(theorem):
                if log_level >= pomagma.util.LOG_LEVEL_DEBUG:
                    log_print(f"proved {theorem}")
                if diverge_count + converge_count == 0:
                    theorems.write("# divergence theorems proved by pomagma\n")
                theorems.write(theorem)
                theorems.write("\n")

            for line in lines:
                assert line.startswith("EQUAL BOT ")
                term_string = line[len("EQUAL BOT ") :]
                term = parse_term(term_string)
                try:
                    try_converge(term, max_steps)
                    conjectures.write(line)
                    conjectures.write("\n")
                    conjecture_count += 1
                except Diverged:
                    theorem = f"EQUAL BOT {term_string}"
                    write_theorem(theorem)
                    diverge_count += 1
                except Converged:
                    theorem = f"NLESS {term_string} BOT"
                    write_theorem(theorem)
                    converge_count += 1
    if log_level >= pomagma.util.LOG_LEVEL_INFO:
        log_print(f"Proved {diverge_count} diverge theorems")
        log_print(f"Proved {converge_count} converge theorems")
        log_print(f"Failed to prove {conjecture_count} conjectures")
    return diverge_count + converge_count


################################################################
# Commands


@parsable
def print_terms(atoms="x,y", max_atom_count=3):
    """Print all terms up to some max atom count.

    atoms is a comma-delimited list of atoms.

    """
    atoms = atoms.split(",")
    for term in iter_terms(atoms, max_atom_count):
        print(print_term(term))


@parsable
def count_terms(max_count=8):
    """Count all terms up to some max atom count."""
    atom_counts = list(range(1, 1 + max_count))
    max_counts = list(range(1, 1 + max_count))

    def count(a, m):
        return sum(1 for term in iter_terms(list(range(a)), m))

    print("\t" * (max_count // 2) + "|atoms|")
    print("\t".join(["|term|"] + [str(a) for a in atom_counts]))
    print("-" * 8 * (1 + max_count))
    for m in max_counts:
        counts = [count(a, m) for a in atom_counts if a + m <= max_count + 1]
        print("\t".join(map(str, [m, *counts])))


@parsable
def may_diverge(atoms="I,K,F,B,C,W,S,Y", max_atom_count=4, max_steps=20):
    """Print terms that have not been proven to converge."""
    atoms = atoms.split(",")
    for term in iter_terms(atoms, max_atom_count):
        try:
            try_converge(term, max_steps)
            print(term)
        except Diverged:
            print(term)
        except Converged:
            pass


@parsable
def must_diverge(atoms="I,K,F,B,C,W,S,Y", max_atom_count=4, max_steps=20):
    """Print terms that have been proven to diverge."""
    atoms = atoms.split(",")
    for term in iter_terms(atoms, max_atom_count):
        try:
            try_converge(term, max_steps)
        except Converged:
            pass
        except Diverged:
            print(term)


if __name__ == "__main__":
    parsable()
