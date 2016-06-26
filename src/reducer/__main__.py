from parsable import parsable
from pomagma.reducer import transforms
from pomagma.reducer.code import polish_parse
from pomagma.reducer.code import polish_print
import os
import pomagma.util
import subprocess
import sys


@parsable
def reduce(*args):
    """Reduce each argument."""
    binary = os.path.join(pomagma.util.BIN, 'reducer', 'cli')
    proc = subprocess.Popen([binary] + list(args))
    proc.wait()
    if proc.returncode == -11:
        sys.stdout.write('Error:\n')
        trace = pomagma.util.get_stack_trace(binary, proc.pid)
        sys.stdout.write(trace)
    return proc.returncode  # Returns number of errors.


@parsable
def compile(string):
    """Compile code from I,K,B,C,S to FUN,LET form."""
    code = polish_parse(string)
    result = transforms.compile_(code)
    print('In: {}'.format(string))
    print('Out: {}'.format(polish_print(result)))


@parsable
def decompile(string):
    """Deompile code from FUN,LET to I,K,B,C,S form."""
    code = polish_parse(string)
    result = transforms.deresult(code)
    print('In: {}'.format(string))
    print('Out: {}'.format(polish_print(result)))


if __name__ == '__main__':
    parsable()
