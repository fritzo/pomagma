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
    requires_auth = lambda fun: skipped
else:
    requires_auth = lambda fun: fun


def load(filename):
    with open(filename) as f:
        return f.read()


def dump(text, filename):
    with open(filename, 'w') as f:
        f.write(text)


@requires_auth
def test_s3():
    text = random_uuid()
    filename = '{}.store_test.test_s3'.format(random_uuid())
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        with in_temp_dir():
            dump(text, filename)
            print 'putting to s3...',
            pomagma.store.s3_lazy_put(filename)
            print 'done'
        assert_true(pomagma.store.s3_exists(filename))
        with in_temp_dir():
            print 'getting from s3...',
            pomagma.store.s3_lazy_get(filename)
            print 'done'
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)
        print 'removing from s3...',
        pomagma.store.s3_remove(filename)
        print 'done'
        assert_false(pomagma.store.s3_exists(filename))


def test_bzip2():
    text = random_uuid()
    filename = '{}.store_test.test_bzip2'.format(random_uuid())
    with in_temp_dir():
        dump(text, filename)
        filename_bz2 = pomagma.store.bzip2(filename)
        assert_true(os.path.exists(filename_bz2))
        os.remove(filename)
        pomagma.store.bunzip2(filename_bz2)
        assert_true(os.path.exists(filename))
        assert_equal(load(filename), text)


@requires_auth
def test_no_cache():
    text = random_uuid()
    filename = '{}.store_test.test_no_cache'.format(random_uuid())
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        with in_temp_dir():
            dump(text, filename)
            pomagma.store.put(filename)
        with in_temp_dir():
            pomagma.store.get(filename)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)
            pomagma.store.remove(filename)


@requires_auth
def test_cache():
    text = random_uuid()
    filename = '{}.store_test.test_cache'.format(random_uuid())
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        with in_temp_dir():
            dump(text, filename)
            pomagma.store.put(filename)
            os.remove(filename)
            pomagma.store.get(filename)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)
            pomagma.store.remove(filename)


@requires_auth
def test_stale_cache():
    text = random_uuid()
    stale_text = random_uuid()
    filename = '{}.store_test.test_stale_cache'.format(random_uuid())
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        with in_temp_dir():
            dump(text, filename)
            pomagma.store.put(filename)
            dump(stale_text, filename)
            pomagma.store.bzip2(filename)
            pomagma.store.get(filename)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)
            pomagma.store.remove(filename)
