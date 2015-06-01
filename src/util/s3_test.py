import os
from nose import SkipTest
from nose.tools import assert_equal, assert_true, assert_false
import mock
import pomagma.util.s3
from pomagma.util import random_uuid, in_temp_dir


TEST_BUCKET = pomagma.util.s3.try_connect_s3('pomagma-test')


def skipped():
    raise SkipTest()


if TEST_BUCKET is None:
    def requires_auth(fun):
        return skipped
else:
    def requires_auth(fun):
        return fun


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
    with mock.patch('pomagma.util.s3.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_s3'):
            text = random_uuid()
            with in_temp_dir():
                dump(text, filename)
                print 'putting to s3...',
                pomagma.util.s3.s3_lazy_put(filename)
                print 'done'
            assert_true(pomagma.util.s3.s3_exists(filename))
            with in_temp_dir():
                print 'getting from s3...',
                pomagma.util.s3.s3_lazy_get(filename)
                print 'done'
                assert_true(os.path.exists(filename))
                assert_equal(load(filename), text)
            print 'removing from s3...',
            pomagma.util.s3.s3_remove(filename)
            print 'done'
            assert_false(pomagma.util.s3.s3_exists(filename))


def test_bzip2():
    for filename in examples('.store_test.test_bzip2'):
        text = random_uuid()
        with in_temp_dir():
            dump(text, filename)
            filename_ext = pomagma.util.s3.bzip2(filename)
            assert_true(os.path.exists(filename_ext))
            os.remove(filename)
            pomagma.util.s3.bunzip2(filename_ext)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)


def test_7z():
    for filename in examples('.store_test.test_7z'):
        text = random_uuid()
        with in_temp_dir():
            dump(text, filename)
            filename_ext = pomagma.util.s3.archive_7z(filename)
            assert_true(os.path.exists(filename_ext))
            os.remove(filename)
            pomagma.util.s3.extract_7z(filename_ext)
            assert_true(os.path.exists(filename))
            assert_equal(load(filename), text)


@requires_auth
def test_no_cache():
    with mock.patch('pomagma.util.s3.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_no_cache'):
            text = random_uuid()
            with in_temp_dir():
                dump(text, filename)
                pomagma.util.s3.put(filename)
            with in_temp_dir():
                pomagma.util.s3.get(filename)
                assert_true(os.path.exists(filename))
                assert_equal(load(filename), text)
                pomagma.util.s3.remove(filename)


@requires_auth
def test_cache():
    with mock.patch('pomagma.util.s3.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_cache'):
            text = random_uuid()
            with in_temp_dir():
                dump(text, filename)
                pomagma.util.s3.put(filename)
                os.remove(filename)
                pomagma.util.s3.get(filename)
                assert_true(os.path.exists(filename))
                assert_equal(load(filename), text)
                pomagma.util.s3.remove(filename)


@requires_auth
def test_stale_cache():
    with mock.patch('pomagma.util.s3.BUCKET', new=TEST_BUCKET):
        for filename in examples('.store_test.test_stale_cache'):
            text = random_uuid()
            stale_text = random_uuid()
            with in_temp_dir():
                dump(text, filename)
                pomagma.util.s3.put(filename)
                dump(stale_text, filename)
                pomagma.util.s3.bzip2(filename)
                pomagma.util.s3.get(filename)
                assert_true(os.path.exists(filename))
                assert_equal(load(filename), text)
                pomagma.util.s3.remove(filename)
