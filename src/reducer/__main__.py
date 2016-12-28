import sys

from parsable import parsable

from pomagma.reducer import bohm, curry, lib
from pomagma.reducer.bohm import polish_simplify, print_tiny, sexpr_simplify
from pomagma.reducer.engines import engine
from pomagma.reducer.linker import link
from pomagma.reducer.syntax import (polish_parse, polish_print, sexpr_parse,
                                    sexpr_print)
from pomagma.util import debuggable

FORMATS = {
    'polish': (polish_parse, polish_print, polish_simplify),
    'sexpr': (sexpr_parse, sexpr_print, sexpr_simplify),
    'tiny': (sexpr_parse, print_tiny, sexpr_simplify),
}


ENGINES = {
    'bohm': bohm,
    'engine': engine,
}


def guess_format(string):
    if '(' in string or ')' in string:
        return 'sexpr'
    else:
        return 'polish'


@parsable
def compile(string, fmt='auto'):
    """Compile code from Bohm ABS to I,K,B,C,S form.

    Available foramts: polish, sexpr

    """
    if fmt == 'auto':
        fmt = guess_format(string)
    print('Format: {}'.format(fmt))
    print('In: {}'.format(string))
    parse, print_, simplify = FORMATS[fmt]
    code = parse(string)
    compiled = curry.compile_(code)
    result = print_(compiled)
    print('Out: {}'.format(result))
    return result


@parsable
def decompile(string, fmt='auto'):
    """Decompile code from Curry I,K,B,C,S to Bohm ABS form.

    Available foramts: polish, sexpr

    """
    if fmt == 'auto':
        fmt = guess_format(string)
    print('Format: {}'.format(fmt))
    print('In: {}'.format(string))
    parse, print_, simplify = FORMATS[fmt]
    decompiled = simplify(string)
    result = print_(decompiled)
    print('Out: {}'.format(result))
    return result


@parsable
def repl(fmt='sexpr'):
    """Read eval print loop."""
    parse, print_, simplify = FORMATS[fmt]
    while True:
        sys.stdout.write('> ')
        sys.stdout.flush()
        try:
            string = raw_input()
        except KeyboardInterrupt:
            sys.stderr.write('Bye!\n')
            sys.stderr.flush()
            return
        try:
            code = parse(string)
            result = bohm.reduce(code)
            result_string = print_(result)
            sys.stdout.write(result_string)
            sys.stdout.write('\n')
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(str(e))
            sys.stderr.write('\n')
            sys.stderr.flush()
            continue


@parsable
def profile(engine='engine', count=256):
    """Run a reduce(lib.byte_test(lib.byte_table[n])) for the first count
    bytes."""
    engine = ENGINES[engine]
    examples = sorted(lib.byte_table.items())
    for n, byte in examples[:count]:
        engine.reduce(lib.byte_test(byte))
        sys.stdout.write('.')
        sys.stdout.flush()


@parsable
def reduce(string, engine='engine', fmt='auto'):
    """Reduce code.

    Args:
        string: code to reduce, in some parsable format specified by fmt
        engine: 'engine', 'bohm'
        fmt: one of 'auto', 'polish', or 'sexpr'

    """
    if fmt == 'auto':
        fmt = guess_format(string)
    if engine not in ENGINES:
        raise ValueError('Unknown engine {}, try one of: {}'.format(
            engine, ', '.join(ENGINES.keys())))
    print('Format: {}'.format(fmt))
    print('Engine: {}'.format(engine))
    print('In: {}'.format(string))
    parse, print_, simplify = FORMATS[fmt]
    code = parse(string)
    code = link(code)
    result = ENGINES[engine].reduce(code)
    result_string = print_(result)
    print('Out: {}'.format(result_string))
    return result_string


@parsable
@debuggable
def step(string, steps=10, fmt='auto'):
    """Step through reduction sequence of bohm library."""
    if fmt == 'auto':
        fmt = guess_format(string)
    print('Format: {}'.format(fmt))
    parse, print_, simplify = FORMATS[fmt]
    code = simplify(string)
    print(print_(code))
    for step in xrange(steps):
        code = bohm.try_compute_step(code)
        if code is None:
            print('DONE')
            return step
        print(print_(code))
    return None


if __name__ == '__main__':
    parsable()
