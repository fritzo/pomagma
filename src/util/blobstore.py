import hashlib
import os
import pomagma.util
import re
import stat
import time

GRACE_PERIOD_SEC = 3600 * 24 * 7  # 1 week
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
    '''return path to read-only file'''
    return os.path.join(pomagma.util.BLOB_DIR, hexdigest)


def create_blob():
    '''return temp_path to write blob to'''
    if not hasattr(create_blob, 'counter'):
        create_blob.counter = 0
    count = create_blob.counter
    create_blob.counter += 1
    filename = 'temp.{}.{}'.format(os.getpid(), count)
    path = os.path.join(pomagma.util.BLOB_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    return path


def store_blob(temp_path):
    '''return digest for future find_blob calls; removes temp file'''
    assert os.path.exists(temp_path)
    hexdigest = hash_file(temp_path)
    path = find_blob(hexdigest)
    if os.path.exists(path):
        os.remove(temp_path)
        os.utime(path)  # touch
    else:
        os.rename(temp_path, path)
    return hexdigest


def load_blob_ref(filename):
    '''return hexdigest read from file'''
    with open(filename, 'rb') as f:
        hexdigest = f.read()
    assert len(hexdigest) == 40, hexdigest
    return hexdigest


def dump_blob_ref(hexdigest, filename):
    '''write hexdigest to file'''
    assert len(hexdigest) == 40, hexdigest
    with os.open(filename, 'wb', 0444) as f:
        f.write(hexdigest)


def garbage_collect(used_blobs, grace_period_sec=GRACE_PERIOD_SEC):
    '''
    Remove all files in BLOB_DIR that:
    (1) are not reachable from refs within max_depth references; and
    (2) have not been touched within grace_period_sec.
    '''
    assert grace_period_sec >= 0, grace_period_sec
    for string in used_blobs:
        assert RE_BLOB.match(string), string
    used_blobs = set(used_blobs)
    deadline = time.time() - grace_period_sec
    count = 0
    for path in os.listdir(pomagma.util.BLOB_DIR):
        if os.path.basename(path) not in used_blobs:
            if os.path.getmtime(path) < deadline:
                os.remove(path)
                count += 1
    print 'removed {} files from {}'.format(count, pomagma.util.BLOB_DIR)


def validate_blobs():
    '''validate SHA1 and mode of all blobs; raise ValueError on error'''
    blobs = sorted(
        blob
        for blob in os.listdir(pomagma.util.BLOB_DIR)
        if RE_BLOB.match(blob)
    )
    print 'validating {} blobs'.format(len(blobs))
    for blob in blobs:
        hexdigest = hash_file(os.path.join(pomagma.util.BLOB_DIR, blob))
        if blob != hexdigest:
            raise ValueError('invalid blob {}'.format(blob))
    for blob in blobs:
        mode = oct(os.stat(blob)[stat.ST_MODE])[-3:]
        if mode != '444':
            raise ValueError('invalid mode {} of blob {}'.format(mode, blob))
