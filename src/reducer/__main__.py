from parsable import parsable
from pomagma.reducer import continuation
from pomagma.reducer import de_bruijn
from pomagma.reducer import engine
from pomagma.reducer import lib
from pomagma.reducer import transforms
from pomagma.reducer.code import polish_parse, polish_print
from pomagma.reducer.code import sexpr_parse, sexpr_print
from pomagma.reducer.linker import link
import os
import pomagma.util
import subprocess
import sys


FORMATS = {
    'polish': (polish_parse, polish_print),
    'sexpr': (sexpr_parse, sexpr_print),
}


def guess_format(string):
    if '(' in string or ')' in string:
        return 'sexpr'
    else:
        return 'polish'


@parsable
def compile(string, fmt='auto'):
    """Compile code from I,K,B,C,S to FUN,LET form.

    Available foramts: polish, sexpr

    """
    if fmt == 'auto':
        fmt = guess_format(string)
    print('Format: {}'.format(fmt))
    parse, print_ = FORMATS[fmt]
    code = parse(string)
    result = transforms.compile_(code)
    print('In: {}'.format(string))
    print('Out: {}'.format(print_(result)))


@parsable
def decompile(string, fmt='auto'):
    """Deompile code from FUN,LET to I,K,B,C,S form.

    Available foramts: polish, sexpr

    """
    if fmt == 'auto':
        fmt = guess_format(string)
    print('Format: {}'.format(fmt))
    print('In: {}'.format(string))
    parse, print_ = FORMATS[fmt]
    code = parse(string)
    result = transforms.decompile(code)
    print('Out: {}'.format(print_(result)))


@parsable
def repl(fmt='sexpr'):
    """Read eval print loop."""
    parse, print_ = FORMATS[fmt]
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
            result = engine.reduce(code)
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
def profile(count=256):
    """Run a reduce(lib.gyte_test(lib.byte_table[n])) for the first count
    bytes."""
    examples = sorted(lib.byte_table.items())
    for n, byte in examples[:count]:
        engine.reduce(lib.byte_test(byte))
        sys.stdout.write('.')
        sys.stdout.flush()


@parsable
def reduce_cpp(*args):
    """Reduce each argument using C++ engine."""
    binary = os.path.join(pomagma.util.BIN, 'reducer', 'cli')
    proc = subprocess.Popen([binary] + list(args))
    proc.wait()
    if proc.returncode == -11:
        sys.stdout.write('Error:\n')
        trace = pomagma.util.get_stack_trace(binary, proc.pid)
        sys.stdout.write(trace)
    return proc.returncode  # Returns number of errors.


ENGINES = {
    'engine': engine,
    'continuation': continuation,
    'de_bruijn': de_bruijn,
}


@parsable
def reduce(string, engine='engine', fmt='auto'):
    """Reduce code.

    Args:
        string: code to reduce, in some parsable format specified by fmt
        engine: 'engine', 'continuation', or 'de_bruijn'
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
    parse, print_ = FORMATS[fmt]
    code = parse(string)
    code = link(code, lazy=False)
    result = ENGINES[engine].reduce(code)
    result_string = print_(result)
    print('Out: {}'.format(result_string))
    return result_string


if __name__ == '__main__':
    parsable()
