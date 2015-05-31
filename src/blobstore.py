import os
import hashlib
import stat
import pomagma.util

BLOB_DIR = os.environ.get(
    'POMAGMA_BLOB_DIR',
    os.path.join(pomagma.util.DATA, 'blob'))


def hash_file(filename):
    sha = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            block = f.read(8192)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def find_blob(hexdigest):
    return os.path.join(BLOB_DIR, '{}.gz'.format(hexdigest))


def create_blob():
    if not hasattr(create_blob, 'counter'):
        create_blob.counter = 0
    count = create_blob.counter
    create_blob.counter += 1
    path = os.path.join(BLOB_DIR, 'temp.{}.{}.gz'.format(os.getpid(), count))
    if os.path.exists(path):
        os.remove(path)
    return path


def store_blob(temp_path):
    assert os.path.exists(temp_path)
    hexdigest = hash_file(temp_path)
    path = find_blob(hexdigest)
    if os.path.exists(path):
        os.remove(temp_path)
    else:
        os.rename(temp_path, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return hexdigest
