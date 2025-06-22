import glob
import os
import re
import shutil
import signal
import sys
import time

from parsable import parsable

import pomagma.io.blobstore
import pomagma.util
import pomagma.workers
from pomagma import analyst, atlas, cartographer, linguist, surveyor, theorist
from pomagma.util import DB, suggest_region_sizes

parsable = parsable.Parsable()

THEORY = os.environ.get("POMAGMA_THEORY", "skja")


# as suggested in http://stackoverflow.com/questions/974189
def raise_keyboard_interrupt(signum, frame):
    raise KeyboardInterrupt


def already_exists(path):
    # like os.path.exists, but ignores bootstrapped worlds
    return os.path.exists(path) and not os.path.islink(path)


@parsable
def test(theory=THEORY, extra_size=0, **options):
    """Test theory by building a world map.

    Options: log_level, log_file
    """
    buildtype = "debug" if pomagma.util.debug else "release"
    path = os.path.join(pomagma.util.DATA, "test", buildtype, "atlas", theory)
    if os.path.exists(path):
        os.system(f"rm -f {path}/*")
    else:
        os.makedirs(path)
    with pomagma.util.chdir(path), pomagma.util.mutex(block=False):
        options.setdefault("log_file", "test.log")
        world = DB("test.world")
        diverge_conjectures = "diverge_conjectures.facts"
        diverge_theorems = "diverge_theorems.facts"
        equal_conjectures = "equal_conjectures.facts"
        equal_theorems = "equal_theorems.facts"

        size = pomagma.util.MIN_SIZES[theory] + extra_size
        surveyor.init(theory, world, size, **options)

        with cartographer.load(theory, world, **options) as db:
            db.validate()
            for priority in [0, 1]:
                while db.infer(priority):
                    db.validate()
            db.conjecture(diverge_conjectures, equal_conjectures)
            theorist.try_prove_diverge(
                diverge_conjectures, diverge_conjectures, diverge_theorems, **options
            )
            db.assume(diverge_theorems)
            db.validate()
            db.dump(world)

        theorist.try_prove_nless(
            theory,
            world,
            equal_conjectures,
            equal_conjectures,
            equal_theorems,
            **options,
        )

        with cartographer.load(theory, world, **options) as db:
            db.assume(equal_theorems)
            db.validate()
            for priority in [0, 1]:
                while db.infer(priority):
                    db.validate()
            db.dump(world)

        with analyst.load(theory, world, **options) as db:
            fail_count = db.test_inference()
            assert fail_count == 0, "analyst.test_inference failed"
    print(f"Theory {theory} appears valid.")


@parsable
def init(theory=THEORY, **options):
    """Initialize world map for given theory.

    Options: log_level, log_file
    """
    log_file = options.setdefault("log_file", "init.log")
    world_size = pomagma.util.MIN_SIZES[theory]
    pomagma.util.log_print(f"initialize to {world_size}", log_file)
    with atlas.chdir(theory, init=True):
        survey = DB("survey")
        world = DB("world")
        normal = DB("world.normal")
        with pomagma.util.temp_copy(survey) as temp:
            surveyor.init(theory, temp, world_size, **options)
        with atlas.load(theory, survey, **options) as db:
            assert not already_exists(world), world
            assert not already_exists(normal), normal
            db.validate()
            db.dump(world)
            db.dump(normal)


@parsable
def explore(
    theory=THEORY,
    max_size=pomagma.workers.DEFAULT_SURVEY_SIZE,
    step_size=512,
    region_queue_size=4,
    **options,
):
    """Continuously expand world map for given theory, inferring and surveying.

    Options: log_level, log_file, deadline_sec
    """
    assert step_size > 0
    region_size = max_size - step_size
    min_size = pomagma.util.MIN_SIZES[theory]
    assert region_size >= min_size
    region_size = max(min_size, max_size - step_size)
    workers = [
        pomagma.workers.cartographer(theory, region_size, region_queue_size, **options),
        pomagma.workers.surveyor(theory, step_size, **options),
    ]
    try:
        for worker in workers:
            worker.wait()
    finally:
        for worker in workers:
            worker.terminate()


@parsable
def make(
    theory=THEORY,
    max_size=pomagma.workers.DEFAULT_SURVEY_SIZE,
    step_size=512,
    **options,
):
    """Initialize; explore.

    Options: log_level, log_file, deadline_sec
    """
    path = os.path.join(pomagma.util.DATA, "atlas", theory)
    if not already_exists(path):
        init(theory, **options)
    explore(theory, max_size, step_size, **options)


@parsable
def update_theory(theory=THEORY, dry_run=False, **options):
    """Update (small) world map after theory changes, and note changes.

    Options: log_level, log_file
    """
    print(dry_run)
    with atlas.chdir(theory):
        world = DB("world")
        updated = pomagma.util.temp_name(DB("world"))
        assert already_exists(world), "First initialize world map"
        options.setdefault("log_file", "update_theory.log")
        atlas.update_theory(theory, world, updated, dry_run=dry_run, **options)


@parsable
def update_language(theory=THEORY, **options):
    """Update world map after language changes.

    Options: log_level, log_file
    """
    with atlas.chdir(theory):
        world = DB("world")
        init = pomagma.util.temp_name(DB("init"))
        aggregate = pomagma.util.temp_name(DB("aggregate"))
        assert already_exists(world), "First initialize world map"
        options.setdefault("log_file", "update_language.log")
        init_size = pomagma.util.MIN_SIZES[theory]
        surveyor.init(theory, init, init_size, **options)
        atlas.update_language(theory, init, world, aggregate, **options)


@parsable
def theorize(theory=THEORY, **options):
    """Make conjectures based on atlas and update atlas based on theorems."""
    with atlas.chdir(theory):
        world = DB("world")
        diverge_conjectures = "diverge_conjectures.facts"
        diverge_theorems = "diverge_theorems.facts"
        equal_conjectures = "equal_conjectures.facts"
        nless_theorems = "nless_theorems.facts"
        assert already_exists(world), "First build world map"
        options.setdefault("log_file", "theorize.log")

        with atlas.load(theory, world, **options) as db:
            db.conjecture(diverge_conjectures, equal_conjectures)
            with pomagma.util.temp_copy(diverge_conjectures) as temp:
                theorem_count = theorist.try_prove_diverge(
                    diverge_conjectures, temp, diverge_theorems, **options
                )
            if theorem_count > 0:
                db.assume(diverge_theorems)
                db.dump(world)

        with pomagma.util.temp_copy(equal_conjectures) as temp:
            theorem_count = theorist.try_prove_nless(
                theory, world, equal_conjectures, temp, nless_theorems, **options
            )
        if theorem_count > 0:
            with atlas.load(theory, world, **options) as db:
                db.assume(nless_theorems)
                db.dump(world)


@parsable
def trim(theory=THEORY, parallel=True, **options):
    """Trim a set of normal regions for running analyst on small machines.

    Options: log_level, log_file
    """
    with atlas.chdir(theory):
        options.setdefault("log_file", "trim.log")
        with cartographer.load(theory, DB("world.normal"), **options) as db:
            min_size = pomagma.util.MIN_SIZES[theory]
            max_size = db.info()["item_count"]
            sizes = suggest_region_sizes(min_size, max_size)
            tasks = [
                {
                    "size": size,
                    "temperature": 0,
                    "filename": DB("region.normal.{:d}").format(size),
                }
                for size in sizes
            ]
            if parallel:
                print(f"Trimming {len(sizes)} regions of sizes {sizes[0]}-{sizes[-1]}")
                db.trim(tasks)
            else:
                for task in tasks:
                    print("Trimming region of size {}".format(task["size"]))
                    db.trim([task])


def _analyze(theory=THEORY, size=None, address=analyst.ADDRESS, **options):
    with atlas.chdir(theory):
        options.setdefault("log_file", "analyst.log")
        if size is None:
            world = DB("world.normal")
        else:
            world = DB(f"region.normal.{size}")
        assert os.path.exists(world), "First initialize normalized world"
        return analyst.serve(theory, world, address=address, **options)


@parsable
def analyze(theory=THEORY, size=None, address=analyst.ADDRESS, **options):
    """Run analyst server on normalized world map.

    Set size=? to list available sizes.
    Options: log_level, log_file
    """
    if size == "?":
        with atlas.chdir(theory):
            files = glob.glob(DB("region.normal.*"))
            sizes = sorted(int(re.search("\\d+", f).group()) for f in files)
        print("Try one of: {}".format(" ".join(str(s) for s in sizes)))
        sys.exit(1)
    server = _analyze(theory, size, address, **options)
    try:
        server.wait()
    except KeyboardInterrupt:
        print("stopping analyst")
    finally:
        server.stop()


@parsable
def connect(address=analyst.ADDRESS):
    """Connect to analyst and start python client."""
    startup = os.path.join(pomagma.util.SRC, "analyst", "startup.py")
    os.environ["PYTHONSTARTUP"] = startup
    os.system("python")


@parsable
def fit_language(theory, address=analyst.ADDRESS, **options):
    """Fit language to corpus, saving results to git working tree.

    Options: log_level, log_file
    """
    options.setdefault("log_file", "linguist.log")
    linguist.fit_language(theory, address=address, **options)


match_atlas = re.compile(r"^atlas\.20\d\d(-\d\d)*").match
default_tag = time.strftime("%Y-%m-%d", time.gmtime())


def list_s3_atlases():
    import pomagma.io.s3

    filenames = pomagma.io.s3.listdir()
    return {m.group() for m in map(match_atlas, filenames) if m}


@parsable
def pull(tag="<most recent>", force=False):
    """
    Pull atlas from s3.
    """
    import pomagma.io.s3

    if not os.path.exists(pomagma.util.DATA):
        os.makedirs(pomagma.util.DATA)
    with pomagma.util.chdir(pomagma.util.DATA):
        master = "atlas"
        if os.path.exists(master):
            if force:
                shutil.rmtree(master)
            else:
                raise OSError("atlas exists; first remove atlas")
        if tag == "<most recent>":
            atlases = list_s3_atlases()
            if not atlases:
                raise OSError(
                    "No atlases available on S3 (S3 connection may have failed)"
                )
            snapshot = max(atlases)
        else:
            snapshot = f"atlas.{tag}"
            assert match_atlas(snapshot), f"invalid tag: {tag}"
        print(f"pulling {snapshot}")
        pomagma.io.s3.pull(f"{snapshot}/")
        blobs = [os.path.join("blob", blob) for blob in atlas.find_used_blobs(snapshot)]
        print(f"pulling {len(blobs)} blobs")
        pomagma.io.s3.pull(*blobs)
        pomagma.io.blobstore.validate_blobs()
        pomagma.io.s3.snapshot(snapshot, master)  # only after validation


@parsable
def push(tag=default_tag, force=False):
    """
    Push atlas to s3.
    """
    import pomagma.io.s3

    pomagma.io.blobstore.validate_blobs()
    with pomagma.util.chdir(pomagma.util.DATA):
        master = "atlas"
        assert os.path.exists(master), "atlas does not exist"
        snapshot = f"atlas.{tag}"
        assert match_atlas(snapshot), f"invalid tag: {tag}"
        atlases = list_s3_atlases()
        if snapshot in atlases and not force:
            raise OSError(f"snapshot already exists: {snapshot}")
        print(f"pushing {snapshot}")
        pomagma.io.s3.snapshot(master, snapshot)
        blobs = [os.path.join("blob", blob) for blob in atlas.find_used_blobs(snapshot)]
        pomagma.io.s3.push(snapshot, *blobs)


@parsable
def gc(grace_period_days=pomagma.io.blobstore.GRACE_PERIOD_DAYS):
    """Garbage collect blobs and validate remaining blobs."""
    atlas.garbage_collect(grace_period_days)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, raise_keyboard_interrupt)
    sys.argv[0] = "pomagma"
    parsable()
