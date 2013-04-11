'''
Wrapper for Amazon S3 and compression.

References:
http://boto.readthedocs.org/en/latest/ref/s3.html
https://github.com/boto/boto/blob/develop/boto/s3
'''

import os
import sys
import subprocess
import boto


def try_connect_s3(bucket):
    try:
        return boto.connect_s3().get_bucket(bucket)
    except boto.exception.NoAuthHandlerFound:
        sys.stderr.write(
            'WARNING failed to connect to s3 bucket {}\n'.format(bucket))
        sys.stderr.flush()
        return None


BUCKET = try_connect_s3('pomagma')


def s3_lazy_put(filename):
    '''
    Put file to s3 only if out of sync.
    '''
    key = BUCKET.get_key(filename)
    if key is None:
        key = BUCKET.new_key(filename)
        key.set_contents_from_filename(filename)
    else:
        with open(filename) as f:
            md5 = key.compute_md5(f)
        if md5 != key.md5:
            key.set_contents_from_filename(filename, md5=md5)
    return key


def s3_lazy_get(filename):
    '''
    Get file from s3 only if out of sync.
    '''
    key = BUCKET.get_key(filename)
    if key is not None:
        if os.path.exists(filename):
            with open(filename) as f:
                md5 = key.compute_md5(f)
            if md5 == key.md5:
                return key
        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        key.get_contents_to_filename(filename)
    return key


def s3_listdir(prefix):
    return BUCKET.list(prefix)


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
    _silent_check_call(['7z', 'a', '-y', filename_ext, filename])
    return filename_ext


def extract_7z(filename_ext):
    assert filename_ext[-3:] == '.7z', filename_ext
    filename = filename_ext[:-3]
    if os.path.exists(filename):
        os.remove(filename)
    _silent_check_call(['7z', 'x', '-y', filename_ext])
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


def listdir(prefix):
    for filename_ext in s3_listdir(prefix):
        assert filename_ext[-len(EXT):] == EXT, filename_ext
        yield filename_ext[:-len(EXT)].lstrip('/')


def remove(filename):
    if os.path.exists(filename):
        os.remove(filename)
    filename_ext = filename + EXT
    if os.path.exists(filename_ext):
        os.remove(filename_ext)
    s3_remove(filename_ext)
