from nose.tools import assert_equal
from pomagma.atlas import get_hash
from pomagma.atlas.bootstrap import THEORY
from pomagma.atlas.bootstrap import WORLD
from pomagma.util.testing import for_each
import pomagma.cartographer


@for_each(['world.h5', 'world.pb'])
def test_formats(filename):
    with pomagma.util.in_temp_dir():
        print 'dumping', filename
        with pomagma.cartographer.load(THEORY, WORLD) as db:
            db.validate()
            db.dump(filename)
        print 'loading', filename
        with pomagma.cartographer.load(THEORY, filename) as db:
            db.validate()
        assert_equal(get_hash(filename), get_hash(WORLD))
