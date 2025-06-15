"""Wrapper for Amazon S3 and compression.

References:
http://boto.readthedocs.org/en/latest/ref/s3.html
https://github.com/boto/boto/blob/develop/boto/s3

"""

import contextlib
import functools
import hashlib
import multiprocessing
import operator
import os
import re
import subprocess

import boto3
from botocore.exceptions import ClientError
from parsable import parsable

import pomagma.util

parsable = parsable.Parsable()


def try_connect_s3(bucket):
    if pomagma.util.TRAVIS_CI:
        print("WARNING avoid connecting to bucket on travis-ci")
        return None
    try:
        s3 = boto3.client("s3")
        # Test access by trying to head the bucket
        s3.head_bucket(Bucket=bucket)
        print("connected to bucket", bucket)
        return s3
    except Exception as e:
        print(f"WARNING failed to connect to s3 bucket {bucket}\n", e)
        return None


# TODO allow different buckets to be specified, e.g. for a logging bucket
BUCKET_NAME = os.environ.get("POMAGMA_BUCKET", "pomagma")
BUCKET = try_connect_s3(BUCKET_NAME)


def s3_lazy_put(filename, assume_immutable=False) -> str | None:
    """Put file to s3 only if out of sync."""
    if BUCKET is None:
        print("WARNING: S3 not available, skipping upload of", filename)
        return None

    try:
        # Check if object exists
        BUCKET.head_object(Bucket=BUCKET_NAME, Key=filename)
        object_exists = True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            object_exists = False
        else:
            raise

    if not object_exists:
        print("uploading", filename)
        BUCKET.upload_file(filename, BUCKET_NAME, filename)
        return filename

    if object_exists and assume_immutable:
        return filename

    # Check if local file is newer
    local_stat = os.stat(filename)

    try:
        remote_obj = BUCKET.head_object(Bucket=BUCKET_NAME, Key=filename)
        local_mtime = local_stat.st_mtime
        remote_mtime = remote_obj["LastModified"].timestamp()

        if local_mtime > remote_mtime:
            print("uploading", filename)
            BUCKET.upload_file(filename, BUCKET_NAME, filename)
            return filename
        print("current", filename)
        return filename
    except ClientError:
        print("uploading", filename)
        BUCKET.upload_file(filename, BUCKET_NAME, filename)
        return filename


def s3_lazy_get(filename, assume_immutable=False):
    """Get file from s3 only if out of sync."""
    if BUCKET is None:
        print("WARNING: S3 not available, cannot download", filename)
        return None

    try:
        # Check if object exists
        response = BUCKET.head_object(Bucket=BUCKET_NAME, Key=filename)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print("missing", filename)
            return None
        raise

    if os.path.exists(filename):
        if assume_immutable:
            # print('already synchronized')
            return filename
        # Calculate local file MD5
        with open(filename, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        key_etag = response["ETag"].strip('"')
        if file_hash == key_etag:
            # print('already synchronized')
            return filename

    dirname = os.path.dirname(filename)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)
    print("downloading", filename)
    BUCKET.download_file(BUCKET_NAME, filename, filename)
    return filename


def s3_listdir(prefix):
    if BUCKET is None:
        print("WARNING: S3 not available, returning empty list")
        return []

    response = BUCKET.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if "Contents" not in response:
        return []
    return [obj for obj in response["Contents"] if not obj["Key"].endswith("/")]


def s3_remove(filename):
    if BUCKET is None:
        print("WARNING: S3 not available, skipping removal of", filename)
        return

    with contextlib.suppress(ClientError):
        BUCKET.delete_object(Bucket=BUCKET_NAME, Key=filename)


def s3_exists(filename):
    if BUCKET is None:
        return False

    try:
        BUCKET.head_object(Bucket=BUCKET_NAME, Key=filename)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def bzip2(filename):
    subprocess.check_call(["bzip2", "--keep", "--force", filename])
    return filename + ".bz2"


def bunzip2(filename_ext):
    assert filename_ext[-4:] == ".bz2", filename_ext
    filename = filename_ext[:-4]
    subprocess.check_call(["bunzip2", "--keep", "--force", filename_ext])
    return filename


def _silent_check_call(args):
    with open(os.devnull, "w") as devnull:
        subprocess.check_call(args, stderr=devnull, stdout=devnull)


def archive_7z(filename):
    filename_ext = filename + ".7z"
    if os.path.exists(filename_ext):
        os.remove(filename_ext)
    print("compressing", filename)
    _silent_check_call(["7z", "a", "-y", filename_ext, filename])
    return filename_ext


def extract_7z(filename_ext):
    assert filename_ext[-3:] == ".7z", filename_ext
    filename = filename_ext[:-3]
    if os.path.exists(filename):
        os.remove(filename)
    print("extracting", filename_ext)
    _silent_check_call(["7z", "x", "-mtm=off", "-y", filename_ext])
    return filename


ARCHIVE = archive_7z
EXTRACT = extract_7z
EXT = ".7z"


# blobs are immutable and compressed
def is_blob(filename):
    if re.match("[a-z0-9]{40}$", os.path.basename(filename)):
        # This only works on local files:
        # mode = oct(os.stat(filename).st_mode)[-3:]
        # assert mode == '444', 'invalid blob mode: {}'.format(mode)
        return True
    return False


def get(filename):
    if is_blob(filename):
        result = s3_lazy_get(filename, assume_immutable=True)
        if result is not None:
            os.chmod(filename, 0o444)
    else:
        filename_ext = filename + EXT
        result = s3_lazy_get(filename_ext)
        if result is not None:
            EXTRACT(filename_ext)


def put(filename):
    if is_blob(filename):
        s3_lazy_put(filename, assume_immutable=True)
    else:
        filename_ext = ARCHIVE(filename)
        s3_lazy_put(filename_ext)


def listdir(prefix=""):
    for key in s3_listdir(prefix):
        if is_blob(key["Key"]):
            filename = key["Key"]
        else:
            filename_ext = key["Key"]
            assert filename_ext[-len(EXT) :] == EXT, filename_ext
            filename = filename_ext[: -len(EXT)]
        yield filename


def remove(filename):
    if os.path.exists(filename):
        os.remove(filename)
    if is_blob(filename):
        s3_remove(filename)
    else:
        filename_ext = filename + EXT
        if os.path.exists(filename_ext):
            os.remove(filename_ext)
        s3_remove(filename_ext)


def parallel_map(fun, args):
    if len(args) <= 1:
        return list(map(fun, args))
    return multiprocessing.Pool().map(fun, args)


def filter_cache(filenames):
    return [
        f
        for f in filenames
        if f[-len(EXT) :] != EXT
        if not os.path.exists(f) or os.path.isfile(f)
    ]


BLACKLIST = re.compile("(test|core|temp|mutex|queue|socket|7z)")


def find(path):
    if os.path.isdir(path):
        return list(
            filter(
                os.path.isfile,
                [
                    os.path.abspath(os.path.join(root, filename))
                    for root, dirnames, filenames in os.walk(path)
                    if not BLACKLIST.search(root)
                    for filename in filenames
                    if not BLACKLIST.search(filename)
                ],
            )
        )
    if not BLACKLIST.search(os.path.basename(path)):
        return [os.path.abspath(path)]
    return []


@parsable
def find_s3(prefix=""):
    """
    Find copyable files on S3.
    """
    assert BUCKET
    for filename in listdir(prefix):
        print(filename)


@parsable
def find_local(path="."):
    """Find copyable files on local filesystem."""
    for filename in find(path):
        print(filename)


@parsable
def snapshot(source, destin):
    """Create resursive snapshot of hard links for push/pull."""
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


@parsable
def pull(*filenames):
    """Pull files from S3 into local cache."""
    assert BUCKET
    filenames = functools.reduce(
        operator.iadd,
        [list(listdir(f)) if f.endswith("/") else [f] for f in filenames],
        [],
    )
    parallel_map(get, filter_cache(filenames))


@parsable
def push(*filenames):
    """Push files to S3 from local cache."""
    assert BUCKET
    filenames = functools.reduce(operator.iadd, list(map(find, filenames)), [])
    filenames = list(map(os.path.relpath, filenames))
    parallel_map(put, filter_cache(filenames))


@parsable
def rm(*filenames):
    """Remove files from S3 and local cache."""
    assert BUCKET
    parallel_map(remove, filter_cache(filenames))


if __name__ == "__main__":
    parsable()
