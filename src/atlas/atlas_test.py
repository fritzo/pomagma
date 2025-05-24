import pomagma.cartographer
from pomagma.atlas import get_hash
from pomagma.atlas.bootstrap import THEORY, WORLD


def test_formats():
    filename = "world.pb"
    with pomagma.util.in_temp_dir():
        print("dumping"), filename
        with pomagma.cartographer.load(THEORY, WORLD) as db:
            db.validate()
            db.dump(filename)
        print("loading"), filename
        with pomagma.cartographer.load(THEORY, filename) as db:
            db.validate()
        assert get_hash(filename) == get_hash(WORLD)
