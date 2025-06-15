import sys

from parsable import parsable

from pomagma.reducer import bohm, curry, lib
from pomagma.reducer.bohm import polish_simplify, print_tiny, sexpr_simplify
from pomagma.reducer.linker import link
from pomagma.reducer.syntax import polish_parse, polish_print, sexpr_parse, sexpr_print
from pomagma.util import debuggable

FORMATS = {
    "polish": (polish_parse, polish_print, polish_simplify),
    "sexpr": (sexpr_parse, sexpr_print, sexpr_simplify),
    "tiny": (sexpr_parse, print_tiny, sexpr_simplify),
}


ENGINES = {
    "bohm": bohm,
    "curry": curry,
}


def guess_format(string):
    if "(" in string or ")" in string:
        return "sexpr"
    return "polish"


@parsable
def compile(string, fmt="auto"):
    """Compile term from Bohm ABS to I,K,B,C,S form.

    Available foramts: polish, sexpr

    """
    if fmt == "auto":
        fmt = guess_format(string)
    print(f"Format: {fmt}")
    print(f"In: {string}")
    parse, print_, simplify = FORMATS[fmt]
    term = parse(string)
    compiled = curry.compile_(term)
    result = print_(compiled)
    print(f"Out: {result}")
    return result


@parsable
def decompile(string, fmt="auto"):
    """Decompile term from Curry I,K,B,C,S to Bohm ABS form.

    Available foramts: polish, sexpr

    """
    if fmt == "auto":
        fmt = guess_format(string)
    print(f"Format: {fmt}")
    print(f"In: {string}")
    parse, print_, simplify = FORMATS[fmt]
    decompiled = simplify(string)
    result = print_(decompiled)
    print(f"Out: {result}")
    return result


@parsable
def repl(fmt="sexpr"):
    """Read eval print loop."""
    parse, print_, simplify = FORMATS[fmt]
    while True:
        sys.stdout.write("> ")
        sys.stdout.flush()
        try:
            string = eval(input())
        except KeyboardInterrupt:
            sys.stderr.write("Bye!\n")
            sys.stderr.flush()
            return
        try:
            term = parse(string)
            result = bohm.reduce(term)
            result_string = print_(result)
            sys.stdout.write(result_string)
            sys.stdout.write("\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(str(e))
            sys.stderr.write("\n")
            sys.stderr.flush()
            continue


@parsable
def profile(engine="bohm", count=256):
    """Run a reduce(lib.byte_test(lib.byte_table[n])) for the first count
    bytes."""
    engine = ENGINES[engine]
    examples = sorted(lib.byte_table.items())
    for n, byte in examples[:count]:
        engine.reduce(lib.byte_test(byte))
        sys.stdout.write(".")
        sys.stdout.flush()


@parsable
def simplify(string, engine="bohm", fmt="auto"):
    """Reduce term.

    Args:
        string: term to simplify, in some parsable format specified by fmt
        engine: 'bohm', 'curry'
        fmt: one of 'auto', 'polish', or 'sexpr'

    """
    if fmt == "auto":
        fmt = guess_format(string)
    if engine not in ENGINES:
        raise ValueError(
            "Unknown engine {}, try one of: {}".format(
                engine, ", ".join(list(ENGINES.keys()))
            )
        )
    print(f"Format: {fmt}")
    print(f"Engine: {engine}")
    print(f"In: {string}")
    parse, print_, simplify = FORMATS[fmt]
    term = parse(string)
    term = link(term)
    result = ENGINES[engine].simplify(term)
    result_string = print_(result)
    print(f"Out: {result_string}")
    return result_string


@parsable
def reduce(string, engine="bohm", fmt="auto"):
    """Reduce term.

    Args:
        string: term to reduce, in some parsable format specified by fmt
        engine: 'bohm', 'curry'
        fmt: one of 'auto', 'polish', or 'sexpr'

    """
    if fmt == "auto":
        fmt = guess_format(string)
    if engine not in ENGINES:
        raise ValueError(
            "Unknown engine {}, try one of: {}".format(
                engine, ", ".join(list(ENGINES.keys()))
            )
        )
    print(f"Format: {fmt}")
    print(f"Engine: {engine}")
    print(f"In: {string}")
    parse, print_, simplify = FORMATS[fmt]
    term = parse(string)
    term = link(term)
    result = ENGINES[engine].reduce(term)
    result_string = print_(result)
    print(f"Out: {result_string}")
    return result_string


@parsable
@debuggable
def step(string, steps=10, fmt="auto"):
    """Step through reduction sequence of bohm library."""
    if fmt == "auto":
        fmt = guess_format(string)
    print(f"Format: {fmt}")
    parse, print_, simplify = FORMATS[fmt]
    term = simplify(string)
    print(print_(term))
    for step in range(steps):
        term = bohm.try_compute_step(term)
        if term is None:
            print("DONE")
            return step
        print(print_(term))
    return None


if __name__ == "__main__":
    parsable()
