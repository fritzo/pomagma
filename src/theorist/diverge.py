

I, K, B, C, W, S, TOP = 'I', 'K', 'B', 'C', 'W', 'S', 'TOP'


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
    elif head == TOP:
        raise Converged()
