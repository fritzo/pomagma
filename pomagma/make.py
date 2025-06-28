import os
import platform
from contextlib import ExitStack
from unittest import mock

from parsable import parsable

import pomagma.util
from pomagma import analyst, atlas, cartographer, surveyor, theorist
from pomagma.io import blobstore
from pomagma.util import DB

# On macOS, /usr/bin/time uses -l for verbose output instead of --verbose
_TIME_CMD = (
    "/usr/bin/time -l" if platform.system() == "Darwin" else "/usr/bin/time --verbose"
)

PROFILERS = {
    "time": _TIME_CMD,
    "valgrind": "valgrind --leak-check=full --track-origins=yes",
    "cachegrind": "valgrind --tool=cachegrind",
    "callgrind": "valgrind --tool=callgrind --callgrind-out-file=callgrind.out",
    "helgrind": "valgrind --tool=helgrind --read-var-info=yes",
}


def _test_atlas(theory):
    """
    Test basic operations in one theory:
        init, validate, copy, survey, aggregate,
        conjecture_diverge, conjecture_equal
    """
    buildtype = "debug" if pomagma.util.debug else "release"
    path = os.path.join(pomagma.util.DATA, "test", buildtype, "atlas", theory)
    if os.path.exists(path):
        os.system(f"rm -f {path}/*")
    else:
        os.makedirs(path)
    with ExitStack() as stack:
        with_ = stack.enter_context
        with_(pomagma.util.chdir(path))
        with_(mock.patch("pomagma.util.BLOB_DIR", new=path))
        with_(pomagma.util.mutex(block=False))

        min_size = pomagma.util.MIN_SIZES[theory]
        dsize = min(64, 1 + min_size)
        sizes = [min_size + i * dsize for i in range(10)]
        opts = {"log_file": "test.log", "log_level": 2}
        diverge_conjectures = "diverge_conjectures.facts"
        diverge_theorems = "diverge_theorems.facts"
        equal_conjectures = "equal_conjectures.facts"
        equal_theorems = "equal_theorems.facts"

        surveyor.init(theory, DB(0), sizes[0], **opts)
        changed = atlas.update_theory(theory, DB(0), DB(1), **opts)
        assert not changed
        with cartographer.load(theory, DB(0), **opts) as db:
            db.validate()
            db.dump(DB(1))
            expected_size = atlas.get_item_count(DB(1))
            actual_size = db.info()["item_count"]
            assert actual_size == expected_size
        surveyor.survey(theory, DB(1), DB(2), sizes[1], **opts)
        with cartographer.load(theory, DB(2), **opts) as db:
            db.trim([{"size": sizes[0], "filename": DB(3)}])
        surveyor.survey(theory, DB(3), DB(4), sizes[1], **opts)
        with cartographer.load(theory, DB(2), **opts) as db:
            db.aggregate(DB(4))
            db.dump(DB(5))
        with cartographer.load(theory, DB(5), **opts) as db:
            db.aggregate(DB(0))
            db.dump(DB(6))
            digest5 = atlas.get_hash(DB(5))
            digest6 = atlas.get_hash(DB(6))
            assert digest5 == digest6

            counts = db.conjecture(diverge_conjectures, equal_conjectures)
            assert counts["diverge_count"] > 0, counts["diverge_count"]
            assert counts["equal_count"] > 0, counts["equal_count"]
            if theory != "h4":
                theorem_count = theorist.try_prove_diverge(
                    diverge_conjectures, diverge_conjectures, diverge_theorems, **opts
                )
                assert theorem_count > 0, theorem_count
                counts = db.assume(diverge_theorems)
                assert counts["pos"] + counts["neg"] > 0, counts
                assert counts["ignored"] == 0, counts
                db.validate()
                db.dump(DB(6))
        theorem_count = theorist.try_prove_nless(
            theory, DB(6), equal_conjectures, equal_conjectures, equal_theorems, **opts
        )
        # assert theorem_count > 0, theorem_count

        if theory != "h4":
            with cartographer.load(theory, DB(6), **opts) as db:
                db.assume(equal_theorems)
                if theorem_count > 0:
                    assert counts["merge"] > 0, counts
                db.validate()
                for priority in [0, 1]:
                    while db.infer(priority):
                        db.validate()
                for priority in [0, 1]:
                    assert not db.infer(priority)
                db.dump(DB(7))
            with analyst.load(theory, DB(7), **opts) as db:
                fail_count = db.test_inference()
                assert fail_count == 0, "analyst.test_inference failed"
        blobstore.validate_blobs()


@parsable
def test_atlas(theory="all"):
    """Test atlas exploration and analysis operations."""
    if theory == "all":
        theories = list(pomagma.util.MIN_SIZES.keys())
        theories.sort(key=pomagma.util.MIN_SIZES.__getitem__)
    else:
        theories = [theory]

    for theory in theories:
        print("-" * 78)
        print("Testing", theory)
        _test_atlas(theory)


@parsable
def test_analyst(theory):
    """Test analyst approximation on normalized world map."""
    opts = {"log_file": "test.log", "log_level": 2}
    with atlas.chdir(theory):
        world = DB("world.normal")
        assert os.path.exists(world), "First initialize normalized world"
        with analyst.load(theory, world, **opts) as db:
            fail_count = db.test()
    assert fail_count == 0, f"Failed {fail_count} cases"
    print("Passed analyst test")


@parsable
def profile_misc():
    """Profile misc libraries."""
    buildtype = "debug" if pomagma.util.debug else "release"
    log_file = os.path.join(pomagma.util.DATA, "profile", buildtype + ".log")
    if os.path.exists(log_file):
        os.remove(log_file)
    opts = {"log_file": log_file, "log_level": 2}
    cmds = [
        os.path.abspath(os.path.join(root, filename))
        for root, dirnames, filenames in os.walk(pomagma.util.BIN)
        for filename in filenames
        if filename.endswith("_profile")
    ]
    assert cmds, f"no profiles found in {pomagma.util.BIN}"
    for cmd in cmds:
        print("Profiling", cmd)
        pomagma.util.log_call(cmd, **opts)
    pomagma.util.check_call("cat", log_file)


@parsable
def profile_surveyor(theory="skj", grow_by=64, extra_size=0, tool="time"):
    """Profile surveyor on random region of world.

    Available tools: time, valgrind, cachegrind, callgrind, helgrind

    """
    size = pomagma.util.MIN_SIZES[theory] + extra_size
    with atlas.chdir(theory):
        opts = {"log_file": "profile.log", "log_level": 2}
        region = DB(f"region.normal.{size:d}")
        temp = pomagma.util.temp_name(DB("profile"))
        world = DB("world")
        if not os.path.exists(region):
            print(f"Creating {region} for profile")
            assert os.path.exists(world), "First initialize world map"
            with cartographer.load(theory, world, **opts) as db:
                db.trim([{"size": size, "filename": region}])
        opts.setdefault("runner", PROFILERS.get(tool, tool))
        surveyor.survey(theory, region, temp, size + grow_by, **opts)
        os.remove(temp)


@parsable
def profile_cartographer(theory="skj", extra_size=0, tool="time", infer=True):
    """
    Profile cartographer load-infer-dump on region of world.
    Available tools: time, valgrind, cachegrind, callgrind, helgrind
    """
    size = pomagma.util.MIN_SIZES[theory] + extra_size
    with atlas.chdir(theory):
        opts = {"log_file": "profile.log", "log_level": 2}
        region = DB(f"region.normal.{size:d}")
        temp = pomagma.util.temp_name(DB("profile"))
        world = DB("world")
        world_size = atlas.get_item_count(world)
        if size >= world_size:
            print(f"Using world of size {world_size}")
            region = world
        elif not os.path.exists(region):
            print(f"Creating {region} for profile")
            assert os.path.exists(world), "First initialize world map"
            with cartographer.load(theory, world, **opts) as db:
                db.trim([{"size": size, "filename": region}])
        opts.setdefault("runner", PROFILERS.get(tool, tool))
        with cartographer.load(theory, region, **opts) as db:
            if infer:
                for priority in [0, 1]:
                    count = db.infer(priority)
                    print(f"Proved {count} theorems")
            db.dump(temp)
        print("Hash:", atlas.get_hash(temp))
        os.remove(temp)


@parsable
def coverity():
    """Check pomagma build with coverity.

    (see http://coverity.com)

    """
    pomagma.util.coverity()


if __name__ == "__main__":
    parsable()
