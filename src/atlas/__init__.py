from pomagma.atlas.structure_pb2 import Structure
from pomagma.util.blobstore import find_blob
from pomagma.util.blobstore import load_blob_ref
from pomagma.util.protobuf import InFile
import contextlib
import os
import pomagma.cartographer
import pomagma.surveyor
import pomagma.theorist
import pomagma.util
import pomagma.util.blobstore


@contextlib.contextmanager
def chdir(theory, init=False):
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    if init:
        assert not os.path.exists(path), 'World map is already initialized'
        os.makedirs(path)
    else:
        assert os.path.exists(path), 'First initialize world map'
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
            print 'theory did not change'
            os.remove(updated)
            return False
        else:
            print 'theory changed'
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
    return filter(os.path.isfile, [
        os.path.abspath(os.path.join(root, filename))
        for root, dirnames, filenames in os.walk(path)
        for filename in filenames
    ])


def find_used_blobs():
    root = os.path.join(pomagma.util.DATA, 'atlas')
    pb_files = [path for path in find(root) if path.endswith('.pb')]
    used_blobs = set()
    for pb_file in pb_files:
        used_blobs.add(pomagma.blobstore.load_blob_ref(pb_file))
        structure = pb_load(pb_file)
        for hexdigest in structure.blobs:
            blob_path = os.path.join(pomagma.util.BLOB_DIR, hexdigest)
            assert os.path.exists(blob_path), '{} missing blob'.format(pb_file)
            used_blobs.add(str(hexdigest))
    return used_blobs


def get_ext(filename):
    parts = filename.split('.')
    while parts[-1] in ['gz', 'bz2', '7z']:
        parts = parts[:-1]
    ext = parts[-1]
    assert ext in ['h5', 'pb'], 'unsupported filetype: {}'.format(filename)
    return ext


@contextlib.contextmanager
def h5_open(filename):
    import tables
    structure = tables.openFile(filename)
    yield structure
    structure.close()


def pb_load(filename):
    with InFile(find_blob(load_blob_ref(filename))) as f:
        structure = Structure()
        f.read(structure)
        return structure


def count_obs(structure):
    points = structure.getNode('/carrier/points')
    item_dim = max(points)
    item_count, = points.shape
    return item_dim, item_count


def get_hash(filename):
    ext = get_ext(filename)
    if ext == 'h5':
        with h5_open(filename) as structure:
            digest = structure.getNodeAttr('/', 'hash').tolist()
            hexdigest = ''.join('{:02x}'.format(x) for x in digest)
            return hexdigest
    elif ext == 'pb':
        return pb_load(filename).hash  # FIXME this is a string, not a list


def get_info(filename):
    ext = get_ext(filename)
    if ext == 'h5':
        with h5_open(filename) as structure:
            item_dim, item_count = count_obs(structure)
    elif ext == 'pb':
        item_count = pb_load(filename).carrier.item_count
        item_dim = item_count
    return {'item_dim': item_dim, 'item_count': item_count}


def get_item_count(filename):
    return get_info(filename)['item_count']


def print_info(filename):
    ext = get_ext(filename)
    if ext == 'h5':
        with h5_open(filename) as structure:
            item_dim, item_count = count_obs(structure)
            print 'item_dim =', item_dim
            print 'item_count =', item_count
            for o in structure:
                print o
    elif ext == 'pb':
        structure = pb_load(filename)
        print 'item_dim =', structure.carrier.item_count
        print 'item_count =', structure.carrier.item_count
        print structure
