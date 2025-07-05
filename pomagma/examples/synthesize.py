from parsable import parsable

import pomagma.analyst
from pomagma.analyst.synthesize import synthesize_from_facts
from pomagma.compiler.expressions import Expression, Expression_2
from pomagma.compiler.parser import parse_string_to_expr, parse_theory_string
from pomagma.compiler.simplify import simplify_expr
from pomagma.compiler.sugar import desugar_expr

APP = Expression_2("APP")
K = Expression("K")
F = Expression("F")


def parse_expr(string):
    return desugar_expr(parse_string_to_expr(string))


def parse_facts(string):
    facts = parse_theory_string(string)["facts"]
    facts = list(map(desugar_expr, facts))
    for fact in facts:
        for var in fact.vars:
            assert len(var.name) > 2, f"unbound variable: {var}"
    return facts


A_THEORY = (
    """
    EQUAL conj FUN s FUN r FUN f COMP r COMP f s
    EQUAL conj FUN s FUN r FUN f COMP COMP r f s
    EQUAL raise FUN x FUN y x
    EQUAL lower FUN x APP x TOP
    EQUAL pull FUN x FUN y JOIN x APP DIV y
    EQUAL push FUN x APP x BOT

    # the existing A moves
    EQUAL move1 PAIR I I
    EQUAL move2 PAIR push pull
    EQUAL move3 PAIR lower raise
    EQUAL move4 ABIND r1 s1 ABIND r2 s2 PAIR COMP r2 r1 COMP s1 s2
    EQUAL move5 ABIND r1 s1 ABIND r2 s2"""
    """ PAIR APP APP conj s1 r2 APP APP conj r1 s2
    LESS move1 A
    LESS move2 A
    LESS move3 A
    LESS move4 A
    LESS move5 A

    # we search for an additional move that provides something new
    LESS hole A
    LESS APP hole B I   # this is too weak
    EQUAL APP hole B I  # this may be too strong
    NLESS APP hole CB I
    NLESS hole move1
    NLESS hole move2
    NLESS hole move3
    NLESS hole move4
    NLESS hole move5
    """
)


@parsable
def define_a(
    max_solutions=15,
    max_memory=pomagma.analyst.synthesize.MAX_MEMORY,
    verbose=1,
    address=pomagma.analyst.ADDRESS,
):
    """
    Search for definition of A = Join {<r, s> | r o s [= I}.
    Tip: use pyprofile and snakeviz to profile this function:
    $ pyprofile -o define_a.pstats -s time pomagma/examples/synthesize.py define_a
    $ snakeviz define_a.pstats
    """
    assert max_solutions > 0, max_solutions
    assert 0 < max_memory and max_memory < 1, max_memory
    facts = parse_facts(A_THEORY)
    hole = Expression("hole")
    initial_sketch = parse_expr("HOLE")
    language = {
        "APP": 1.0,
        # 'COMP': 1.6,
        "JOIN": 3.0,
        "B": 1.0,
        "C": 1.3,
        "A": 2.0,
        "BOT": 2.0,
        "TOP": 2.0,
        "I": 2.2,
        # 'Y': 2.3,
        "K": 2.6,
        "S": 2.7,
        "J": 2.8,
        "DIV": 3.0,
    }
    with pomagma.analyst.connect(address) as db:
        results = synthesize_from_facts(
            db=db,
            facts=facts,
            var=hole,
            initial_sketch=initial_sketch,
            language=language,
            max_solutions=max_solutions,
            max_memory=max_memory,
            verbose=verbose,
        )
    print("Possible Fillings:")
    APP = Expression_2("APP")
    f = Expression("f")
    for complexity, term, filling in results:
        print(simplify_expr(APP(filling, f)))
    return results


@parsable
def define_a_pair(
    max_solutions=15,
    max_memory=pomagma.analyst.synthesize.MAX_MEMORY,
    verbose=1,
    address=pomagma.analyst.ADDRESS,
):
    """
    Search for definition of A = Join {<r, s> | r o s [= I}.
    Tip: use pyprofile and snakeviz to profile this function:
    $ pyprofile -o define_a.pstats -s time pomagma/examples/synthesize.py define_a
    $ snakeviz define_a.pstats
    """
    assert max_solutions > 0, max_solutions
    assert 0 < max_memory and max_memory < 1, max_memory
    facts = parse_facts(A_THEORY)
    hole = Expression("hole")
    initial_sketch = parse_expr("PAIR HOLE HOLE")
    language = {
        "APP": 1.0,
        # 'COMP': 1.6,
        "JOIN": 3.0,
        "B": 1.0,
        "C": 1.3,
        # 'A': 2.0,
        "BOT": 2.0,
        "TOP": 2.0,
        "I": 2.2,
        # 'Y': 2.3,
        "K": 2.6,
        "S": 2.7,
        "J": 2.8,
        "DIV": 3.0,
    }
    with pomagma.analyst.connect(address) as db:
        results = synthesize_from_facts(
            db=db,
            facts=facts,
            var=hole,
            initial_sketch=initial_sketch,
            language=language,
            max_solutions=max_solutions,
            max_memory=max_memory,
            verbose=verbose,
        )
    print("Possible Fillings:")
    for complexity, term, filling in results:
        print(f"<{simplify_expr(APP(filling, K))},\t{simplify_expr(APP(filling, F))}>")
    return results


if __name__ == "__main__":
    parsable()
