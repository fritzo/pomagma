import sys
import subprocess
from app import PORT
from pomagma.analyst import ADDRESS

PYTHON = sys.executable


def serve(port=PORT, address=ADDRESS, reloader=True):
    '''
    Start editor server.
    '''
    proc = subprocess.Popen([
        PYTHON, '-m', 'pomagma.editor.app', 'serve',
        'port={}'.format(port),
        'address={}'.format(address),
        'reloader={}'.format(reloader),
    ])
    return proc
