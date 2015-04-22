import os
import contextlib
import pomagma.util
import pomagma.surveyor
import pomagma.cartographer
import pomagma.theorist


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
        size = pomagma.util.get_item_count(world)
        old_hash = pomagma.util.get_hash(world)
        pomagma.surveyor.survey(theory, world, updated, size, **opts)
        new_hash = pomagma.util.get_hash(updated)
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
