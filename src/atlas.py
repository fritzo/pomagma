import os
import pomagma.util
import pomagma.cartographer
import pomagma.theorist


def load(theory, world, address=None, **opts):
    with pomagma.util.mutex(world):
        with pomagma.cartographer.load(theory, world, address, **opts) as db:
            yield db


def initialize(theory, world, source, **opts):
    with pomagma.util.mutex(world):
        assert not os.path.exists(world)
        with pomagma.cartographer.load(theory, source, **opts) as db:
            db.validate()
        os.rename(source, world)


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
        pomagma.theorist.assume(world, updated, theorems, **opts)
        with pomagma.cartographer.load(theory, world, **opts) as db:
            db.validate()
        os.rename(updated, world)
