from pomagma.reducer.code import APP, JOIN, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import complexity
from pomagma.reducer.continuations import CONT_TOP, CONT_BOT
from pomagma.reducer.continuations import cont_hnf, IVAR
from pomagma.reducer.engines import de_bruijn
from pomagma.reducer.util import list_to_stack
from pomagma.util.testing import for_each

x = IVAR(0)
y = IVAR(1)

CONT_x = de_bruijn.cont_from_codes((x,))
CONT_y = de_bruijn.cont_from_codes((y,))
CONT_S = de_bruijn.cont_from_codes((S,))
CONT_KS = de_bruijn.cont_from_codes((APP(K, S),))
CONT_JOIN_x_y = de_bruijn.cont_from_codes((JOIN(x, y),))
CONT_JOIN_x_S = de_bruijn.cont_from_codes((JOIN(x, S),))


@for_each([x, y, TOP, BOT, I, K, B, C, S])
def test_cont_complexity_eq_code_complexity(code):
    cont = de_bruijn.cont_from_codes((code,))
    assert de_bruijn.cont_complexity(cont) == complexity(code)


@for_each([
    (TOP, [], 0, 0),
    (BOT, [], 0, 0),
    (x, [], 0, 1),
    (x, [], 1, 1 + 1),
    (x, [], 2, 1 + 2),
    (x, [CONT_TOP], 0, 1 + 1),
    (x, [CONT_TOP], 1, 1 + 1 + 1),
    (x, [CONT_TOP], 2, 1 + 1 + 2),
    (x, [CONT_BOT], 0, 1 + 1),
    (x, [CONT_BOT], 1, 1 + 1 + 1),
    (x, [CONT_BOT], 2, 1 + 1 + 2),
    (x, [CONT_x], 0, 1 + 1),
    (x, [CONT_x], 1, 1 + 1 + 1),
    (x, [CONT_S], 0, 1 + max(6, 1)),
    (x, [CONT_x, CONT_TOP], 0, 1 + max(1 + max(1, 0), 1)),
    (x, [CONT_x, CONT_TOP], 1, 1 + max(1 + max(1, 0), 1) + 1),
    (x, [CONT_x, CONT_TOP, CONT_KS], 0, 8),
    (S, [CONT_x, CONT_TOP, CONT_KS], 0, 9),
    (x, [CONT_JOIN_x_y], 0, 1 + max(1, 1)),
    (x, [CONT_JOIN_x_S], 0, 1 + max(1, 6)),
])
def test_cont_complexity(code, args, bound, expected):
    stack = list_to_stack(args)
    if code is TOP:
        cont = CONT_TOP
    elif code is BOT:
        cont = CONT_BOT
    else:
        cont = cont_hnf(code, stack, bound)
    assert de_bruijn.cont_complexity(cont) == expected
