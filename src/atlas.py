import os
import contextlib
import pomagma.util
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


def translate(theory, init, world, aggregate, **opts):
    assert os.path.exists(init)
    assert not os.path.exists(aggregate)
    with pomagma.util.mutex(world):
        assert os.path.exists(world)
        with pomagma.cartographer.load(theory, init, **opts) as db:
            db.aggregate(world)
            db.validate()
            db.dump(aggregate)
        os.rename(aggregate, world)
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
