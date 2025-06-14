import os

from parsable import parsable

import pomagma.atlas
import pomagma.util


@parsable
def info(filename):
    """Print info about a structure file."""
    pomagma.atlas.print_info(filename)


@parsable
def cp(theory, source, destin):
    """Copy and recompress structure file."""
    assert source != destin
    with pomagma.util.mutex(source):
        assert os.path.exists(source)
        assert not os.path.exists(destin)
        with pomagma.cartographer.load(theory, source) as db:
            db.dump(destin)


@parsable
def blobs(root):
    """Find all blobs referenced under a root directory."""
    for blob in pomagma.atlas.find_used_blobs(root):
        print(blob)


parsable()
