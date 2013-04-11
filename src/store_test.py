import os
from nose import SkipTest
from nose.tools import assert_equal, assert_true, assert_false
import mock
import pomagma.store
from pomagma.util import random_uuid, in_temp_dir


TEST_BUCKET = pomagma.store.try_connect_s3('pomagma-test')


def skipped():
    raise SkipTest()


if TEST_BUCKET is None:
    requires_auth = skipped
else:
    requires_auth = lambda fun: fun


def load(filename):
    with open(filename) as f:
        return f.read()


def dump(text, filename):
    with open(filename, 'w') as f:
        f.write(text)


@requires_auth
def test_s3_put_get():
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        text = random_uuid()
        filename = '{}.store_test.test_s3_put_get'.format(random_uuid())
        with in_temp_dir():
            dump(text, filename)
            print 'putting to s3...',
            pomagma.store.s3_put(filename)
            print 'done'
        assert_true(pomagma.store.s3_exists(filename))
        with in_temp_dir():
            print 'getting from s3...',
            pomagma.store.s3_get(filename)
            print 'done'
            assert_true(os.path.exists(filename))
            assert_equal(text, load(filename))
        print 'removing from s3...',
        pomagma.store.s3_remove(filename)
        print 'done'
        assert_false(pomagma.store.s3_exists(filename))
