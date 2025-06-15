import contextlib
import os

import pomagma.cartographer
import pomagma.surveyor
import pomagma.theorist
import pomagma.util
from pomagma.atlas.structure_pb2 import Structure
from pomagma.io import blobstore
from pomagma.io.protobuf import InFile


@contextlib.contextmanager
def chdir(theory, init=False):
    path = os.path.join(pomagma.util.DATA, "atlas", theory)
    if init:
        assert not os.path.exists(path), "World map is already initialized"
        os.makedirs(path)
    else:
        assert os.path.exists(path), "First initialize world map"
    with pomagma.util.chdir(path):
        yield


@contextlib.contextmanager
def load(theory, world, address=None, **opts):
    with pomagma.util.mutex(world):
        with pomagma.cartographer.load(theory, world, address, **opts) as db:
            yield db


def update_theory(theory, world, updated, dry_run=False, **opts):
    assert not os.path.exists(updated)
    with pomagma.util.mutex(world):
        assert os.path.exists(world)
        size = get_item_count(world)
        old_hash = get_hash(world)
        pomagma.surveyor.survey(theory, world, updated, size, **opts)
        new_hash = get_hash(updated)
        if new_hash == old_hash:
            print("theory did not change")
            os.remove(updated)
            return False
        print("theory changed")
        if dry_run:
            os.remove(updated)
        else:
            os.rename(updated, world)
        return True


def update_language(theory, init, world, updated, **opts):
    assert os.path.exists(init)
    assert not os.path.exists(updated)
    with pomagma.util.mutex(world):
        assert os.path.exists(world)
        with pomagma.cartographer.load(theory, init, **opts) as db:
            db.aggregate(world)
            db.validate()
            db.dump(updated)
        os.rename(updated, world)
    os.remove(init)


def update_format(theory, source, destin, **opts):
    print(f"converting {theory} {source} -> {destin}")
    assert source != destin
    with pomagma.util.mutex(source):
        assert os.path.exists(source)
        assert not os.path.exists(destin)
        with pomagma.cartographer.load(theory, source, **opts) as db:
            db.validate()
            db.dump(destin)


def assume(theory, world, updated, theorems, **opts):
    assert not os.path.exists(updated)
    with pomagma.util.mutex(world):
        assert os.path.exists(world)
        with pomagma.cartographer.load(theory, world, **opts) as db:
            db.assume(theorems)
            db.validate()
            db.dump(updated)
        os.rename(updated, world)


def find(path):
    return list(
        filter(
            os.path.isfile,
            [
                os.path.abspath(os.path.join(root, filename))
                for root, dirnames, filenames in os.walk(path)
                for filename in filenames
            ],
        )
    )


def find_used_blobs(root):
    root = os.path.abspath(root)
    used_blobs = set()
    for filename in find(root):
        if filename.endswith(".pb"):
            with open(filename) as f:
                for line in f:
                    hexdigest = line.strip()
                    assert blobstore.RE_BLOB.match(hexdigest), hexdigest
                    used_blobs.add(hexdigest)
    return used_blobs


def garbage_collect(grace_period_days=blobstore.GRACE_PERIOD_DAYS):
    used_blobs = find_used_blobs(pomagma.util.DATA)
    blobstore.garbage_collect(used_blobs, grace_period_days)
    blobstore.validate_blobs()


def get_ext(filename):
    parts = filename.split(".")
    while parts[-1] in ["gz", "bz2", "7z"]:
        parts = parts[:-1]
    ext = parts[-1]
    assert ext in ["pb"], f"unsupported filetype: {filename}"
    return ext


def pb_load(filename):
    with InFile(blobstore.find_blob(blobstore.load_blob_ref(filename))) as f:
        structure = Structure()
        f.read(structure)
        return structure


def count_obs(structure):
    points = structure.getNode("/carrier/points")
    item_dim = max(points)
    (item_count,) = points.shape
    return item_dim, item_count


def get_hash(filename):
    assert get_ext(filename) == "pb"
    return pb_load(filename).hash  # FIXME this is a string, not a list


def get_info(filename):
    assert get_ext(filename) == "pb"
    item_count = pb_load(filename).carrier.item_count
    item_dim = item_count
    return {"item_dim": item_dim, "item_count": item_count}


def get_item_count(filename):
    return get_info(filename)["item_count"]


def get_filesize(filename):
    return os.stat(filename).st_size


def print_info(filename):
    assert get_ext(filename) == "pb"
    files = [filename]
    files += list(map(blobstore.find_blob, blobstore.iter_blob_refs(filename)))
    print("file_count =", len(files))
    print("byte_count =", sum(map(get_filesize, files)))
    structure = pb_load(filename)
    print("item_dim =", structure.carrier.item_count)
    print("item_count =", structure.carrier.item_count)
    print(structure)
