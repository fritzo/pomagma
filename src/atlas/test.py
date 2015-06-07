from nose import SkipTest
from nose.tools import assert_equal
from pomagma.atlas.bootstrap import THEORY
from pomagma.atlas.bootstrap import WORLD
from pomagma.util import get_hash
from pomagma.util.testing import for_each
import os
import pomagma.cartographer


@for_each(['world.h5', 'world.pbgz'])
def test_formats(filename):
    with pomagma.util.in_temp_dir():
        if filename.endswith('.pbgz'):
            raise SkipTest('TODO fix protobuf io')
        opts = {'blob_dir': os.getcwd()}
        print 'dumping', filename
        with pomagma.cartographer.load(THEORY, WORLD, **opts) as db:
            db.validate()
            db.dump(filename)
        print 'loading', filename
        with pomagma.cartographer.load(THEORY, filename, **opts) as db:
            db.validate()
        assert_equal(get_hash(filename), get_hash(WORLD))
