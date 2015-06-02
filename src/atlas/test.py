import os
from nose import SkipTest
from nose.tools import assert_equal
from pomagma.atlas.bootstrap import THEORY
from pomagma.atlas.bootstrap import WORLD
from pomagma.util import get_hash
import pomagma.cartographer


def _test_formats(filename):
    with pomagma.util.in_temp_dir():
        if filename.endswith('.pb') or filename.endswith('.pb.gz'):
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


def test_formats():
    yield _test_formats, 'world.h5'
    yield _test_formats, 'world.pb'
    yield _test_formats, 'world.pb.gz'
