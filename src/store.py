'''
Wrapper for Amazon S3 and compression.

References:
http://boto.readthedocs.org/en/latest/ref/s3.html
https://github.com/boto/boto/blob/develop/boto/s3
'''

import os
import re
import subprocess
import multiprocessing
import boto
import parsable
import pomagma.util

parsable = parsable.Parsable()


def try_connect_s3(bucket):
    if pomagma.util.TRAVIS_CI:
        print 'WARNING avoid connecting to bucket on travis-ci'
        return None
    try:
        connection = boto.connect_s3().get_bucket(bucket)
        print 'connected to bucket', bucket
        return connection
    except boto.exception.NoAuthHandlerFound as e:
        print 'WARNING failed to authenticate s3 bucket {}\n'.format(bucket), e
        return None
    except Exception as e:
        print 'WARNING failed to connect to s3 bucket {}\n'.format(bucket), e
        return None


# TODO allow different buckets to be specified, e.g. for a logging bucket
BUCKET = try_connect_s3(os.environ.get('POMAGMA_BUCKET', 'pomagma'))


def s3_lazy_put(filename):
    '''
    Put file to s3 only if out of sync.
    '''
    key = BUCKET.get_key(filename)
    if key is None:
        key = BUCKET.new_key(filename)
        print 'uploading', filename
        key.set_contents_from_filename(filename)
        return key
    else:
        with open(filename, 'rb') as f:
            print 'checking cached', filename
            md5 = key.compute_md5(f)
        key_md5_0 = key.etag.strip('"')  # WTF
        if md5[0] == key_md5_0:
            print 'already synchronized'
            return key
        else:
            print 'uploading', filename
            key.set_contents_from_filename(filename, md5=md5)
            return key


def s3_lazy_get(filename):
    '''
    Get file from s3 only if out of sync.
    '''
    key = BUCKET.get_key(filename)
    if key is None:
        print 'missing', filename
        return key
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            print 'checking cached', filename
            md5 = key.compute_md5(f)
        key_md5_0 = key.etag.strip('"')  # WTF
        if md5[0] == key_md5_0:
            print 'already synchronized'
            return key
    dirname = os.path.dirname(filename)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)
    print 'downloading', filename
    key.get_contents_to_filename(filename)
    return key


def s3_listdir(prefix):
    keys = BUCKET.list(prefix)
    return [key for key in keys if not key.name.endswith('/')]


def s3_remove(filename):
    key = BUCKET.get_key(filename)
    if key is not None:
        key.delete()


def s3_exists(filename):
    key = BUCKET.get_key(filename)
    return key is not None


def bzip2(filename):
    subprocess.check_call(['bzip2', '--keep', '--force', filename])
    filename_ext = filename + '.bz2'
    return filename_ext


def bunzip2(filename_ext):
    assert filename_ext[-4:] == '.bz2', filename_ext
    filename = filename_ext[:-4]
    subprocess.check_call(['bunzip2', '--keep', '--force', filename_ext])
    return filename


def _silent_check_call(args):
    with open(os.devnull, 'w') as devnull:
        subprocess.check_call(args, stderr=devnull, stdout=devnull)


def archive_7z(filename):
    filename_ext = filename + '.7z'
    if os.path.exists(filename_ext):
        os.remove(filename_ext)
    print 'compressing', filename
    _silent_check_call(['7z', 'a', '-y', filename_ext, filename])
    return filename_ext


def extract_7z(filename_ext):
    assert filename_ext[-3:] == '.7z', filename_ext
    filename = filename_ext[:-3]
    if os.path.exists(filename):
        os.remove(filename)
    print 'extracting', filename_ext
    _silent_check_call(['7z', 'x', '-mtm=off', '-y', filename_ext])
    return filename


ARCHIVE = archive_7z
EXTRACT = extract_7z
EXT = '.7z'


def get(filename):
    filename_ext = filename + EXT
    s3_lazy_get(filename_ext)
    return EXTRACT(filename_ext)


def put(filename):
    filename_ext = ARCHIVE(filename)
    s3_lazy_put(filename_ext)


def listdir(prefix=''):
    for key in s3_listdir(prefix):
        filename_ext = key.name
        assert filename_ext[-len(EXT):] == EXT, filename_ext
        filename = filename_ext[:-len(EXT)]
        yield filename


def remove(filename):
    if os.path.exists(filename):
        os.remove(filename)
    filename_ext = filename + EXT
    if os.path.exists(filename_ext):
        os.remove(filename_ext)
    s3_remove(filename_ext)


def parallel_map(fun, args):
    if len(args) <= 1:
        return map(fun, args)
    else:
        return multiprocessing.Pool().map(fun, args)


def filter_cache(filenames):
    return [
        f
        for f in filenames
        if f[-len(EXT):] != EXT
        if not os.path.exists(f) or os.path.isfile(f)
    ]


def find(path):
    blacklist = re.compile('(test|core|temp|mutex|queue|socket|7z)')
    return filter(os.path.isfile, [
        os.path.abspath(os.path.join(root, filename))
        for root, dirnames, filenames in os.walk(path)
        if not blacklist.search(root)
        for filename in filenames
        if not blacklist.search(filename)
    ])


@parsable.command
def find_s3(prefix=''):
    '''
    Find copyable files on S3.
    '''
    assert BUCKET
    for filename in listdir(prefix):
        print filename


@parsable.command
def find_local(path='.'):
    '''
    Find copyable files on local filesystem.
    '''
    for filename in find(path):
        print filename


@parsable.command
def snapshot(source, destin):
    '''
    Create resursive snapshot of hard links for push/pull.
    '''
    assert os.path.isdir(source)
    assert destin != source
    source = os.path.abspath(source)
    destin = os.path.abspath(destin)
    for source_file in find(source):
        relpath = os.path.relpath(source_file, source)
        destin_file = os.path.join(destin, relpath)
        destin_dir = os.path.dirname(destin_file)
        if not os.path.exists(destin_dir):
            os.makedirs(destin_dir)
        if os.path.exists(destin_file):
            os.remove(destin_file)
        os.link(source_file, destin_file)


@parsable.command
def pull(*filenames):
    '''
    Pull files from S3 into local cache.
    '''
    assert BUCKET
    if len(filenames) == 1 and filenames[0].endswith('/'):
        filenames = listdir(filenames[0])
    parallel_map(get, filter_cache(filenames))


@parsable.command
def push(*filenames):
    '''
    Push files to S3 from local cache.
    '''
    assert BUCKET
    if len(filenames) == 1 and os.path.isdir(filenames[0]):
        filenames = map(os.path.relpath, find(filenames[0]))
    parallel_map(put, filter_cache(filenames))


@parsable.command
def rm(*filenames):
    '''
    Remove files from S3 and local cache.
    '''
    assert BUCKET
    parallel_map(remove, filter_cache(filenames))


if __name__ == '__main__':
    parsable.dispatch()
