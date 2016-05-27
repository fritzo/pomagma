from parsable import parsable
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


if __name__ == '__main__':
    parsable()
