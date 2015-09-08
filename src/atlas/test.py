from nose.tools import assert_equal
from pomagma.atlas import get_hash
from pomagma.atlas.bootstrap import THEORY
from pomagma.atlas.bootstrap import WORLD
import pomagma.cartographer


def test_formats():
    filename = 'world.pb'
    with pomagma.util.in_temp_dir():
        print 'dumping', filename
        with pomagma.cartographer.load(THEORY, WORLD) as db:
            db.validate()
            db.dump(filename)
        print 'loading', filename
        with pomagma.cartographer.load(THEORY, filename) as db:
            db.validate()
        assert_equal(get_hash(filename), get_hash(WORLD))
