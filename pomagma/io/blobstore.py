import hashlib
import multiprocessing
import os
import re
import sys
import time

import pomagma.util
from pomagma.io import creat, create_directories

GRACE_PERIOD_DAYS = 7.0
RE_BLOB = re.compile("^[a-z0-9]{40}$")


def hash_file(filename):
    hasher = hashlib.sha1()
    with open(filename, "rb") as f:
        while True:
            block = f.read(8192)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def find_blob(hexdigest: str | bytes) -> str:
    """Return path to read-only file."""
    if isinstance(hexdigest, bytes):
        hexdigest = hexdigest.decode("utf-8")
    return os.path.join(pomagma.util.BLOB_DIR, hexdigest)


def create_blob():
    """Return temp_path to write blob to."""
    create_directories(pomagma.util.BLOB_DIR)
    if not hasattr(create_blob, "counter"):
        create_blob.counter = 0
    count = create_blob.counter
    create_blob.counter += 1
    filename = f"temp.{os.getpid()}.{count}"
    path = os.path.join(pomagma.util.BLOB_DIR, filename)
    if os.path.exists(path):
        print("removing temp file", path)
        os.remove(path)
    return path


def store_blob(temp_path):
    """Return digest for future find_blob calls; removes temp file."""
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
    """Iterate over all hexdigests in ref file."""
    with open(filename, "rb") as f:
        for line in f:
            hexdigest = line.strip().decode("utf-8")
            assert len(hexdigest) == 40, hexdigest
            yield hexdigest


def load_blob_ref(filename):
    """Return root hexdigest from ref file."""
    for root_hexdigest in iter_blob_refs(filename):
        return root_hexdigest
    return None


def dump_blob_ref(root_hexdigest, filename, sub_hexdigests=[]):
    """Write root and sub hexdigests to ref file."""
    assert isinstance(root_hexdigest, str), root_hexdigest
    assert len(root_hexdigest) == 40, root_hexdigest
    with creat(filename, 0o444) as f:
        f.write(root_hexdigest.encode("utf-8"))
        for sub_hexdigest in sub_hexdigests:
            assert isinstance(sub_hexdigest, str), sub_hexdigest
            assert len(sub_hexdigest) == 40, sub_hexdigest
            f.write(b"\n")
            f.write(sub_hexdigest.encode("utf-8"))


def garbage_collect(used_blobs, grace_period_days=GRACE_PERIOD_DAYS):
    """
    Remove all files in BLOB_DIR that:
    (1) are not reachable from refs within max_depth references; and
    (2) have not been touched within grace_period_sec.
    """
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
    print(f"removed {count} files from {pomagma.util.BLOB_DIR}")


def validate_blobs():
    """Validate SHA1 and mode of some or all blobs; raise ValueError on
    error."""
    blobs = sorted(
        blob for blob in os.listdir(pomagma.util.BLOB_DIR) if RE_BLOB.match(blob)
    )
    print(f"validating {len(blobs)} blobs")
    paths = [os.path.join(pomagma.util.BLOB_DIR, blob) for blob in blobs]
    hexdigests = multiprocessing.Pool().map(hash_file, paths)
    errors = [blob for blob, hexdigest in zip(blobs, hexdigests) if blob != hexdigest]
    if errors:
        corrupt = os.path.join(pomagma.util.BLOB_DIR, "corrupt")
        if not os.path.exists(corrupt):
            os.makedirs(corrupt)
        for error in errors:
            os.rename(
                os.path.join(pomagma.util.BLOB_DIR, error), os.path.join(corrupt, error)
            )
        raise ValueError("corrupt blobs; moved to blob/corrupt/")
    for blob in blobs:
        path = os.path.join(pomagma.util.BLOB_DIR, blob)
        mode = oct(os.stat(path).st_mode)[-3:]
        if mode != "444":
            sys.stderr.write(f"WARNING repairing mode of {blob}\n")
            os.chmod(path, 0o444)
