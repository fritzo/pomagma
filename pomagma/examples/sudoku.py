import random

from parsable import parsable

from pomagma.reducer import lib
from pomagma.reducer.programs import program
from pomagma.reducer.sugar import app, combinator
from pomagma.util import TODO


def random_entry(size, density):
    if random.uniform(0, 1) < density:
        return random.randint(1, size)
    return None


def print_entry(entry):
    if entry is None:
        return "  ."
    return f"{entry: 3d}"


def print_grid(grid):
    return "\n".join("".join(map(print_entry, row)) for row in grid)


@parsable
def generate(size=9, density=0.2, seed=0):
    """Generate a random sudoku problem (that may be unsolvable)."""
    assert size >= 0, size
    assert 0 <= density and density <= 1, density
    random.seed(seed)
    grid = [[random_entry(size, density) for j in range(size)] for i in range(size)]
    print(print_grid(grid))
    return grid


def all_different(xs):
    return len(xs) == len(set(xs))


def is_valid(grid):
    size = len(grid)
    rows = grid
    cols = list(zip(*rows))
    diags = [
        [grid[i][i] for i in range(size)],
        [grid[i][size - i - 1] for i in range(size)],
    ]
    return all(all_different(s) for s in rows + cols + diags)


@combinator
def un_all_different(xs):
    return app(
        xs,
        lib.true,
        lambda h, t: lib.bool_and(
            lib.list_all(lambda x: lib.bool_not(lib.list_num_eq(h, x))),
            all_different(t),
        ),
    )


@combinator
def un_is_valid(grid):
    TODO()


py_all_different = program(("list", "num"), "bool")(un_all_different)
py_is_valid = program(("list", ("list", "num")), "bool")(un_is_valid)


if __name__ == "__main__":
    parsable()
