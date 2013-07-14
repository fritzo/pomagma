import os
import pomagma.util
import pomagma.cartographer
import pomagma.theorist


def initialize(world, source, **opts):
    with pomagma.util.mutex(world):
        assert not os.path.exists(world)
        pomagma.cartographer.validate(source, **opts)
        os.rename(source, world)
        # TODO fork and push to s3


def aggregate(world, source, aggregate, **opts):
    assert os.path.exists(source)
    assert not os.path.exists(aggregate)
    with pomagma.util.mutex(world):
        assert os.path.exists(world)
        pomagma.cartographer.aggregate(world, source, aggregate, **opts)
        pomagma.cartographer.validate(aggregate, **opts)
        os.rename(aggregate, world)
        # TODO fork and push to s3
    os.remove(source)


def assume(world, updated, theorems, **opts):
    assert not os.path.exists(updated)
    with pomagma.util.mutex(world):
        assert os.path.exists(world)
        pomagma.theorist.assume(world, updated, theorems, **opts)
        pomagma.cartographer.validate(updated, **opts)
        os.rename(updated, world)
        # TODO fork and push to s3