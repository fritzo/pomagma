'''
Boostrapped data is included in git repo, for testing.
'''

from pomagma.util import DB
import os
import pomagma.util

THEORY = os.environ.get('THEORY', 'skrj')
SIZE = pomagma.util.MIN_SIZES[THEORY]
WORLD = os.path.join(
    pomagma.util.DATA,
    'atlas',
    THEORY,
    DB('region.normal.{:d}'.format(SIZE)))
