import os
import hashlib


BLOB_DIR = os.environ.get('POMAGMA_BLOB_DIR', os.getcwd())


def hash_file(filename):
    sha = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            block = f.read(8192)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def load_blob(hexdigest):
    return os.path.join(BLOB_DIR, hexdigest)


def store_blob(temp_path):
    assert os.path.exists(temp_path)
    hexdigest = hash_file(temp_path)
    path = load_blob(hexdigest)
    if os.path.exists(path):
        os.remove(temp_path)
    else:
        os.rename(temp_path, path)
    return hexdigest
