import os
import hashlib
import pomagma.util


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
