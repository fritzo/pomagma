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
    dirname = os.path.dirname(filename)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(filename, 'w') as f:
        f.write(text)


def examples(suffix):
    for depth in range(3):
        dirs = [random_uuid() for _ in range(depth)]
        filename = random_uuid() + suffix
        path = apply(os.path.join, dirs + [filename])
        yield path


@requires_auth
def test_s3():
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_s3'):
            text = random_uuid()
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
    for filename in examples('.store_test.test_bzip2'):
        text = random_uuid()
        with in_temp_dir():
            dump(text, filename)
            filename_ext = pomagma.store.bzip2(filename)
            assert_true(os.path.exists(filename_ext))
            os.remove(filename)
            pomagma.store.bunzip2(filename_ext)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)


def test_7z():
    for filename in examples('.store_test.test_7z'):
        text = random_uuid()
        with in_temp_dir():
            dump(text, filename)
            filename_ext = pomagma.store.archive_7z(filename)
            assert_true(os.path.exists(filename_ext))
            os.remove(filename)
            pomagma.store.extract_7z(filename_ext)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)


@requires_auth
def test_no_cache():
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_no_cache'):
            text = random_uuid()
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
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_cache'):
            text = random_uuid()
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
    with mock.patch('pomagma.store.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_stale_cache'):
            text = random_uuid()
            stale_text = random_uuid()
            with in_temp_dir():
                dump(text, filename)
                pomagma.store.put(filename)
                dump(stale_text, filename)
                pomagma.store.bzip2(filename)
                pomagma.store.get(filename)
                assert_true(os.path.exists(filename))
                assert_equal(load(filename), text)
                pomagma.store.remove(filename)
