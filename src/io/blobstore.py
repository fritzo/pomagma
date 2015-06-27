from itertools import izip
from pomagma.io import creat
from pomagma.io import create_directories
import hashlib
import os
import pomagma.util
import re
import sys
import multiprocessing
import time

GRACE_PERIOD_DAYS = 7.0
RE_BLOB = re.compile('^[a-z0-9]{40}$')


def hash_file(filename):
    hasher = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            block = f.read(8192)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def find_blob(hexdigest):
    '''Return path to read-only file.'''
    return os.path.join(pomagma.util.BLOB_DIR, hexdigest)


def create_blob():
    '''Return temp_path to write blob to.'''
    create_directories(pomagma.util.BLOB_DIR)
    if not hasattr(create_blob, 'counter'):
        create_blob.counter = 0
    count = create_blob.counter
    create_blob.counter += 1
    filename = 'temp.{}.{}'.format(os.getpid(), count)
    path = os.path.join(pomagma.util.BLOB_DIR, filename)
    if os.path.exists(path):
        print "removing temp file ", path
        os.remove(path)
    return path


def store_blob(temp_path):
    '''Return digest for future find_blob calls; removes temp file.'''
    assert os.path.exists(temp_path)
    hexdigest = hash_file(temp_path)
    path = find_blob(hexdigest)
    if os.path.exists(path):
        os.remove(temp_path)
        os.utime(path)  # touch
    else:
        os.rename(temp_path, path)
    return hexdigest


def iter_blob_refs(filename):
    '''Iterate over all hexdigests in ref file.'''
    with open(filename, 'rb') as f:
        for line in f:
            hexdigest = line.strip()
            assert len(hexdigest) == 40, hexdigest
            yield hexdigest


def load_blob_ref(filename):
    '''Return root hexdigest from ref file.'''
    for root_hexdigest in iter_blob_refs(filename):
        return root_hexdigest


def dump_blob_ref(root_hexdigest, filename, sub_hexdigests=[]):
    '''Write root and sub hexdigests to ref file.'''
    assert isinstance(root_hexdigest, basestring), root_hexdigest
    assert len(root_hexdigest) == 40, root_hexdigest
    with creat(filename, 0444) as f:
        f.write(root_hexdigest)
        for sub_hexdigest in sub_hexdigests:
            assert isinstance(sub_hexdigest, basestring), sub_hexdigest
            assert len(sub_hexdigest) == 40, sub_hexdigest
            f.write('\n')
            f.write(sub_hexdigest)


def garbage_collect(used_blobs, grace_period_days=GRACE_PERIOD_DAYS):
    '''
    Remove all files in BLOB_DIR that:
    (1) are not reachable from refs within max_depth references; and
    (2) have not been touched within grace_period_sec.
    '''
    assert grace_period_days >= 0, grace_period_days
    grace_period_sec = grace_period_days * 24 * 3600
    for string in used_blobs:
        assert RE_BLOB.match(string), string
    used_blobs = set(used_blobs)
    deadline = time.time() - grace_period_sec
    count = 0
    for basename in os.listdir(pomagma.util.BLOB_DIR):
        if basename not in used_blobs:
            path = os.path.join(pomagma.util.BLOB_DIR, basename)
            if os.path.getmtime(path) < deadline:
                os.remove(path)
                count += 1
    print 'removed {} files from {}'.format(count, pomagma.util.BLOB_DIR)


def validate_blobs():
    '''
    Validate SHA1 and mode of some or all blobs; raise ValueError on error.
    '''
    blobs = sorted(
        blob
        for blob in os.listdir(pomagma.util.BLOB_DIR)
        if RE_BLOB.match(blob)
    )
    print 'validating {} blobs'.format(len(blobs))
    paths = [os.path.join(pomagma.util.BLOB_DIR, blob) for blob in blobs]
    hexdigests = multiprocessing.Pool().map(hash_file, paths)
    errors = [
        blob
        for blob, hexdigest in izip(blobs, hexdigests)
        if blob != hexdigest
    ]
    if errors:
        corrupt = os.path.join(pomagma.util.BLOB_DIR, 'corrupt')
        if not os.path.exists(corrupt):
            os.makedirs(corrupt)
        for error in errors:
            os.rename(
                os.path.join(pomagma.util.BLOB_DIR, error),
                os.path.join(corrupt, error))
        raise ValueError('corrupt blobs; moved to blob/corrupt/')
    for blob in blobs:
        path = os.path.join(pomagma.util.BLOB_DIR, blob)
        mode = oct(os.stat(path).st_mode)[-3:]
        if mode != '444':
            sys.stderr.write('WARNING repairing mode of {}\n'.format(blob))
            os.chmod(path, 0444)
