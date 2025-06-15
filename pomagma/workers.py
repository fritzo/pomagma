import glob
import itertools
import multiprocessing
import os
import shutil
import subprocess
import sys
import time

from parsable import parsable

import pomagma.atlas
import pomagma.cartographer
import pomagma.surveyor
import pomagma.theorist
import pomagma.util
from pomagma.util import DB, suggest_region_sizes

parsable = parsable.Parsable()

DEFAULT_SURVEY_SIZE = 16384 + 512 - 1
MIN_SLEEP_SEC = 1
MAX_SLEEP_SEC = 600
PYTHON = sys.executable


class parsable_fork:
    def __init__(self, fun, *args, **kwargs):
        self.args = [PYTHON, "-m", "pomagma.workers", fun.__name__]
        self.args += list(map(str, args))
        for key, val in list(kwargs.items()):
            self.args.append(f"{key}={val}")
        self.proc = subprocess.Popen(self.args)

    def wait(self):
        self.proc.wait()
        code = self.proc.returncode
        assert code == 0, "\n".join(
            [
                f"forked command failed with exit code {code}",
                " ".join(self.args),
            ]
        )

    def terminate(self):
        if self.proc.poll() is None:
            self.proc.terminate()


class fork:
    def __init__(self, fun, *args, **kwargs):
        self.command = "{}({})".format(
            fun.__name__,
            ", ".join(
                [str(arg) for arg in args]
                + [f"{key}={val!r}" for key, val in list(kwargs.items())]
            ),
        )
        self.proc = multiprocessing.Process(target=fun, args=args, kwargs=kwargs)
        self.proc.start()

    def wait(self):
        self.proc.join()
        code = self.proc.exitcode
        assert code == 0, "\n".join(
            [f"forked command failed with exit code {code}", self.command]
        )

    def terminate(self):
        if self.proc.is_alive():
            self.proc.terminate()


class Sleeper:
    def __init__(self, name):
        self.name = name
        self.duration = MIN_SLEEP_SEC

    def reset(self):
        self.duration = MIN_SLEEP_SEC

    def sleep(self):
        sys.stderr.write(f"# {self.name} sleeping\n")
        sys.stderr.flush()
        time.sleep(self.duration)
        self.duration = min(MAX_SLEEP_SEC, 2 * self.duration)


class FileQueue:
    def __init__(self, path, template="{}"):
        self.path = path
        self.template = template
        self.pattern = os.path.join(self.path, DB(template.format("[0-9]*")))

    def get(self):
        # specifically ignore temporary files like temp.1234.0.pb
        return glob.glob(self.pattern)

    def __iter__(self):
        return iter(self.get())

    def __len__(self):
        return len(self.get())

    def try_pop(self, destin):
        for source in self:
            os.rename(source, destin)
            return True
        return False

    def push(self, source):
        if self.path and not os.path.exists(self.path):
            os.makedirs(self.path)
        with pomagma.util.mutex(self.path):
            for i in itertools.count():
                destin = os.path.join(self.path, DB(self.template.format(i)))
                if not os.path.exists(destin):
                    os.rename(source, destin)
                    return

    def clear(self):
        for item in self:
            os.remove(item)


class CartographerWorker:
    def __init__(self, theory, region_size, region_queue_size, **options):
        self.options = options
        self.log_file = options["log_file"]
        self.world = DB("world")
        self.normal_world = DB("world.normal")
        self.normal_region = DB("region.normal.{:d}")
        self.min_size = pomagma.util.MIN_SIZES[theory]
        self.region_size = region_size
        self.region_queue = FileQueue("region.queue")
        self.survey_queue = FileQueue("survey.queue")
        self.region_queue_size = region_queue_size
        self.diverge_conjectures = "diverge_conjectures.facts"
        self.diverge_theorems = "diverge_theorems.facts"
        self.equal_conjectures = "equal_conjectures.facts"
        DEBUG = False
        if DEBUG:
            options = pomagma.util.use_memcheck(options, "cartographer.memcheck.out")
        self.server = pomagma.cartographer.serve(theory, self.world, **options)
        self.db = self.server.connect()
        self.infer_state = 0
        if os.path.exists(self.normal_world):
            world_digest = pomagma.atlas.get_hash(self.world)
            normal_world_digest = pomagma.atlas.get_hash(self.normal_world)
            if world_digest == normal_world_digest:
                self.infer_state = 2

    def stop(self):
        self.db.stop()
        # self.server.stop()

    def log(self, message):
        rss = pomagma.util.get_rss(self.server.pid)
        message = f"Cartographer {rss}k {message}"
        pomagma.util.log_print(message, self.log_file)

    def is_normal(self):
        assert self.infer_state in [0, 1, 2]
        return self.infer_state == 2

    def garbage_collect(self):
        # assume surveyor.dump takes < 1.0 days
        pomagma.atlas.garbage_collect(grace_period_days=1.0)

    def try_work(self):
        return (
            self.try_produce_regions()
            or self.try_normalize()
            or self.try_consume_surveys()
        )

    def try_produce_regions(self):
        queue_size = len(self.region_queue)
        if queue_size >= self.region_queue_size:
            return False
        self.fill_region_queue(self.region_queue)
        return True

    def try_normalize(self):
        if self.is_normal():
            return False
        self.log("Inferring {}".format(["pos", "neg"][self.infer_state]))
        if self.db.infer(self.infer_state):
            self.db.validate()
            self.db.dump(self.world)
            self.garbage_collect()
            self.replace_region_queue()
        else:
            self.infer_state += 1
            if self.is_normal():
                self.log("Normalized")
                self.db.dump(self.normal_world)
                self.trim_normal_regions()
                self.garbage_collect()
                self.theorize()
        return True

    def try_consume_surveys(self):
        surveys = self.survey_queue.get()
        if not surveys:
            return False
        self.log(f"Aggregating {len(surveys)} surveys")
        for survey in surveys:
            self.db.aggregate(survey)
            self.db.validate()
            self.db.dump(self.world)
            self.garbage_collect()
            self.infer_state = 0
            world_size = self.db.info()["item_count"]
            self.log(f"world_size = {world_size}")
            os.remove(survey)
        self.db.crop()
        self.replace_region_queue()
        return True

    def fill_region_queue(self, queue):
        self.log("Filling region queue")
        if not os.path.exists(queue.path):
            os.makedirs(queue.path)
        queue_size = len(queue)
        trim_count = max(0, self.region_queue_size - queue_size)
        regions_out = []
        for i in itertools.count():
            region_out = os.path.join(queue.path, DB(i))
            if not os.path.exists(region_out):
                regions_out.append(region_out)
                if len(regions_out) == trim_count:
                    break
        # trim in parallel because these are small
        self.db.trim([{"size": self.region_size, "filename": r} for r in regions_out])

    def replace_region_queue(self):
        self.log("Replacing region queue")
        with pomagma.util.temp_copy(self.region_queue.path) as temp_path:
            self.fill_region_queue(FileQueue(temp_path))
            self.region_queue.clear()
            self.garbage_collect()

    def trim_normal_regions(self):
        self.log("Trimming normal regions")
        assert self.is_normal()
        max_size = self.db.info()["item_count"]
        # trim sequentially because these are large
        for size in suggest_region_sizes(self.min_size, max_size):
            filename = self.normal_region.format(size)
            self.db.trim([{"size": size, "filename": filename}])

    def theorize(self):
        self.log("Theorizing")
        conjectures = self.diverge_conjectures
        theorems = self.diverge_theorems
        self.db.conjecture(conjectures, self.equal_conjectures)
        with pomagma.util.temp_copy(conjectures) as temp_conjectures:
            with pomagma.util.temp_copy(theorems) as temp_theorems:
                if os.path.exists(theorems):
                    shutil.copyfile(theorems, temp_theorems)
                theorem_count = pomagma.theorist.try_prove_diverge(
                    conjectures, temp_conjectures, temp_theorems, **self.options
                )
        if theorem_count > 0:
            self.log(f"Proved {theorem_count} theorems")
            counts = self.db.assume(theorems)
            if counts["pos"] + counts["neg"]:
                self.log(
                    "Assumed {} pos + {} neg facts".format(counts["pos"], counts["neg"])
                )
                self.db.validate()
                self.db.dump(self.world)
                self.garbage_collect()
                self.infer_state = 0 if counts["pos"] else 1
                self.replace_region_queue()


@parsable
def cartographer_work(
    theory, region_size=(DEFAULT_SURVEY_SIZE - 512), region_queue_size=4, **options
):
    """Start cartographer worker."""
    min_size = pomagma.util.MIN_SIZES[theory]
    assert region_size >= min_size
    options.setdefault("log_file", "cartographer.log")
    with pomagma.atlas.chdir(theory), pomagma.util.mutex(DB("world")):
        worker = CartographerWorker(theory, region_size, region_queue_size, **options)
        try:
            sleeper = Sleeper("cartographer")
            while True:
                if not worker.try_work():
                    sleeper.sleep()
                else:
                    sleeper.reset()
        finally:
            worker.stop()


def cartographer(*args, **kwargs):
    return parsable_fork(cartographer_work, *args, **kwargs)


@parsable
def surveyor_work(theory, step_size=512, **options):
    """Start surveyor worker."""
    assert step_size > 0
    with pomagma.atlas.chdir(theory):
        region_queue = FileQueue("region.queue")
        survey_queue = FileQueue("survey.queue")
        region = pomagma.util.temp_name(DB("region"))
        survey = pomagma.util.temp_name(DB("survey"))
        options.setdefault("log_file", "survey.log")
        sleeper = Sleeper("surveyor")
        while True:
            if not region_queue.try_pop(region):
                sleeper.sleep()
            else:
                sleeper.reset()
                region_size = pomagma.atlas.get_item_count(region)
                survey_size = region_size + step_size
                pomagma.surveyor.survey(theory, region, survey, survey_size, **options)
                os.remove(region)
                survey_queue.push(survey)


def surveyor(*args, **kwargs):
    return parsable_fork(surveyor_work, *args, **kwargs)


if __name__ == "__main__":
    parsable()
