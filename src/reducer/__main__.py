from parsable import parsable
from pomagma.reducer import transforms
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
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
    '''
    Compile code from I,K,B,C,S to FUN,LET form.
    '''
    code = parse(string)
    result = transforms.compile_(code)
    print('In: {}'.format(string))
    print('Out: {}'.format(serialize(result)))


@parsable
def decompile(string):
    '''
    Deompile code from FUN,LET to I,K,B,C,S form.
    '''
    code = parse(string)
    result = transforms.deresult(code)
    print('In: {}'.format(string))
    print('Out: {}'.format(serialize(result)))


if __name__ == '__main__':
    parsable()
