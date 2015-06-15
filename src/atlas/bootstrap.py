'''
Boostrapped data is included in git repo, for testing.
'''

import os
import pomagma.util

THEORY = os.environ.get('THEORY', 'skrj')
SIZE = pomagma.util.MIN_SIZES[THEORY]
WORLD = os.path.join(
    pomagma.util.DATA,
    'atlas',
    THEORY,
    'region.normal.{:d}.pb'.format(SIZE))
