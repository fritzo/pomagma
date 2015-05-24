import os
import re
import sys
import time
import signal
import shutil
import parsable
parsable = parsable.Parsable()
import pomagma.util
import pomagma.workers
from pomagma import analyst
from pomagma import atlas
from pomagma import cartographer
from pomagma import linguist
from pomagma import surveyor
from pomagma import theorist

THEORY = os.environ.get('POMAGMA_THEORY', 'skrj')


# as suggested in http://stackoverflow.com/questions/974189
def raise_keyboard_interrupt(signum, frame):
    raise KeyboardInterrupt()


def already_exists(path):
    # like os.path.exists, but ignores bootstrapped worlds
    return os.path.exists(path) and not os.path.islink(path)


@parsable.command
def test(theory=THEORY, extra_size=0, **options):
    '''
    Test theory by building a world map.
    Options: log_level, log_file
    '''
    buildtype = 'debug' if pomagma.util.debug else 'release'
    path = os.path.join(pomagma.util.DATA, 'test', buildtype, 'atlas', theory)
    if os.path.exists(path):
        os.system('rm -f {}/*'.format(path))
    else:
        os.makedirs(path)
    with pomagma.util.chdir(path), pomagma.util.mutex(block=False):
        options.setdefault('log_file', 'test.log')
        world = 'test.world.h5'
        diverge_conjectures = 'diverge_conjectures.facts'
        diverge_theorems = 'diverge_theorems.facts'
        equal_conjectures = 'equal_conjectures.facts'
        equal_theorems = 'equal_theorems.facts'

        size = pomagma.util.MIN_SIZES[theory] + extra_size
        surveyor.init(theory, world, size, **options)

        with cartographer.load(theory, world, **options) as db:
            db.validate()
            for priority in [0, 1]:
                while db.infer(priority):
                    db.validate()
            db.conjecture(diverge_conjectures, equal_conjectures)
            theorist.try_prove_diverge(
                diverge_conjectures,
                diverge_conjectures,
                diverge_theorems,
                **options)
            db.assume(diverge_theorems)
            db.validate()
            db.dump(world)

        theorist.try_prove_nless(
            theory,
            world,
            equal_conjectures,
            equal_conjectures,
            equal_theorems,
            **options)

        with cartographer.load(theory, world, **options) as db:
            db.assume(equal_theorems)
            db.validate()
            for priority in [0, 1]:
                while db.infer(priority):
                    db.validate()
            db.dump(world)

        with analyst.load(theory, world, **options) as db:
            fail_count = db.test_inference()
            assert fail_count == 0, 'analyst.test_inference failed'
    print 'Theory {} appears valid.'.format(theory)


@parsable.command
def init(theory=THEORY, **options):
    '''
    Initialize world map for given theory.
    Options: log_level, log_file
    '''
    log_file = options.setdefault('log_file', 'init.log')
    world_size = pomagma.util.MIN_SIZES[theory]
    pomagma.util.log_print('initialize to {}'.format(world_size), log_file)
    with atlas.chdir(theory, init=True):
        survey = 'survey.h5'
        world = 'world.h5'
        normal = 'world.normal.h5'
        with pomagma.util.temp_copy(survey) as temp:
            surveyor.init(theory, temp, world_size, **options)
        with atlas.load(theory, survey, **options) as db:
            assert not already_exists(world), world
            assert not already_exists(normal), normal
            db.validate()
            db.dump(world)
            db.dump(normal)


@parsable.command
def explore(
        theory=THEORY,
        max_size=pomagma.workers.DEFAULT_SURVEY_SIZE,
        step_size=512,
        region_queue_size=4,
        **options):
    '''
    Continuously expand world map for given theory, inferring and surveying.
    Options: log_level, log_file
    '''
    assert step_size > 0
    region_size = max_size - step_size
    min_size = pomagma.util.MIN_SIZES[theory]
    assert region_size >= min_size
    region_size = max(min_size, max_size - step_size)
    workers = [
        pomagma.workers.cartographer(
            theory,
            region_size,
            region_queue_size,
            **options),
        pomagma.workers.surveyor(theory, step_size, **options),
    ]
    try:
        for worker in workers:
            worker.wait()
    finally:
        for worker in workers:
            worker.terminate()


@parsable.command
def make(
        theory=THEORY,
        max_size=pomagma.workers.DEFAULT_SURVEY_SIZE,
        step_size=512,
        **options):
    '''
    Initialize; explore.
    Options: log_level, log_file
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    if not already_exists(path):
        init(theory, **options)
    explore(theory, max_size, step_size, **options)


@parsable.command
def update_theory(theory=THEORY, dry_run=False, **options):
    '''
    Update (small) world map after theory changes, and note changes.
    Options: log_level, log_file
    '''
    print dry_run
    with atlas.chdir(theory):
        world = 'world.h5'
        updated = pomagma.util.temp_name('world.h5')
        assert already_exists(world), 'First initialize world map'
        options.setdefault('log_file', 'update_theory.log')
        atlas.update_theory(theory, world, updated, dry_run=dry_run, **options)


@parsable.command
def update_language(theory=THEORY, **options):
    '''
    Update world map after language changes.
    Options: log_level, log_file
    '''
    with atlas.chdir(theory):
        world = 'world.h5'
        init = pomagma.util.temp_name('init.h5')
        aggregate = pomagma.util.temp_name('aggregate.h5')
        assert already_exists(world), 'First initialize world map'
        options.setdefault('log_file', 'update_language.log')
        init_size = pomagma.util.MIN_SIZES[theory]
        surveyor.init(theory, init, init_size, **options)
        atlas.update_language(theory, init, world, aggregate, **options)


@parsable.command
def theorize(theory=THEORY, **options):
    '''
    Make conjectures based on atlas and update atlas based on theorems.
    '''
    with atlas.chdir(theory):
        world = 'world.h5'
        diverge_conjectures = 'diverge_conjectures.facts'
        diverge_theorems = 'diverge_theorems.facts'
        equal_conjectures = 'equal_conjectures.facts'
        nless_theorems = 'nless_theorems.facts'
        assert already_exists(world), 'First build world map'
        options.setdefault('log_file', 'theorize.log')

        with atlas.load(theory, world, **options) as db:
            db.conjecture(diverge_conjectures, equal_conjectures)
            with pomagma.util.temp_copy(diverge_conjectures) as temp:
                theorem_count = theorist.try_prove_diverge(
                    diverge_conjectures,
                    temp,
                    diverge_theorems,
                    **options)
            if theorem_count > 0:
                db.assume(diverge_theorems)
                db.dump(world)

        with pomagma.util.temp_copy(equal_conjectures) as temp:
            theorem_count = theorist.try_prove_nless(
                theory,
                world,
                equal_conjectures,
                temp,
                nless_theorems,
                **options)
        if theorem_count > 0:
            with atlas.load(theory, world, **options) as db:
                db.assume(nless_theorems)
                db.dump(world)


def sparse_range(min_size, max_size):
    assert min_size <= max_size
    sizes = [512]
    while True:
        size = 2 * sizes[-1]
        if size <= max_size:
            sizes.append(size)
        else:
            break
    sizes += [3 * s for s in sizes if 3 * s < max_size]
    sizes = [s - 1 for s in sizes if s > min_size]
    sizes.sort()
    return sizes


@parsable.command
def trim(theory=THEORY, parallel=True, **options):
    '''
    Trim a set of normal regions for running analyst on small machines.
    Options: log_level, log_file
    '''
    with atlas.chdir(theory):
        options.setdefault('log_file', 'trim.log')
        with cartographer.load(theory, 'world.normal.h5', **options) as db:
            min_size = pomagma.util.MIN_SIZES[theory]
            max_size = db.info()['item_count']
            sizes = sparse_range(min_size, max_size)
            tasks = []
            for size in sizes:
                tasks.append({
                    'size': size,
                    'temperature': 0,
                    'filename': 'region.normal.{:d}.h5'.format(size)
                })
            if parallel:
                print 'Trimming {} regions of sizes {}-{}'.format(
                    len(sizes),
                    sizes[0],
                    sizes[-1])
                db.trim(tasks)
            else:
                for task in tasks:
                    print 'Trimming region of size {}'.format(task['size'])
                    db.trim([task])


def _analyze(theory=THEORY, size=None, address=analyst.ADDRESS, **options):
    with atlas.chdir(theory):
        options.setdefault('log_file', 'analyst.log')
        if size is None:
            world = 'world.normal.h5'
        else:
            world = 'region.normal.{}.h5'.format(size)
        assert os.path.exists(world), 'First initialize normalized world'
        return analyst.serve(theory, world, address=address, **options)


@parsable.command
def analyze(theory=THEORY, size=None, address=analyst.ADDRESS, **options):
    '''
    Run analyst server on normalized world map.
    Options: log_level, log_file
    '''
    server = _analyze(theory, size, address, **options)
    try:
        server.wait()
    except KeyboardInterrupt:
        print 'stopping analyst'
    finally:
        server.stop()


@parsable.command
def connect(address=analyst.ADDRESS):
    '''
    Connect to analyst and start python client.
    '''
    startup = os.path.join(pomagma.util.SRC, 'analyst', 'startup.py')
    os.environ['PYTHONSTARTUP'] = startup
    os.system('python')


@parsable.command
def fit_language(theory, address=analyst.ADDRESS, **options):
    '''
    Fit language to corpus, saving results to git working tree.
    Options: log_level, log_file
    '''
    options.setdefault('log_file', 'linguist.log')
    linguist.fit_language(theory, address=address, **options)


match_atlas = re.compile(r'^atlas\.20\d\d(-\d\d)*').match
default_tag = time.strftime('%Y-%m-%d', time.gmtime())


def list_s3_atlases():
    import pomagma.store
    filenames = pomagma.store.listdir()
    return set(m.group() for m in map(match_atlas, filenames) if m)


@parsable.command
def pull(tag='<most recent>'):
    '''
    Pull atlas from s3.
    '''
    import pomagma.store
    if not os.path.exists(pomagma.util.DATA):
        os.makedirs(pomagma.util.DATA)
    with pomagma.util.chdir(pomagma.util.DATA):
        destin = 'atlas'
        assert not os.path.exists(destin), 'atlas exists; first remove atlas'
        if tag == '<most recent>':
            source = max(list_s3_atlases())
        else:
            source = 'atlas.{}'.format(tag)
            assert match_atlas(source), 'invalid tag: {}'.format(tag)
        print 'pulling {} -> {}'.format(source, destin)
        pomagma.store.pull('{}/'.format(source))
        pomagma.store.snapshot(source, destin)


@parsable.command
def push(tag=default_tag):
    '''
    Push atlas to s3.
    '''
    import pomagma.store
    with pomagma.util.chdir(pomagma.util.DATA):
        source = 'atlas'
        assert os.path.exists(source), 'atlas does not exist'
        destin = 'atlas.{}'.format(tag)
        assert match_atlas(destin), 'invalid tag: {}'.format(tag)
        assert destin not in list_s3_atlases(), 'destin already exists'
        print 'pushing {} -> {}'.format(source, destin)
        pomagma.store.snapshot(source, destin)
        pomagma.store.push(destin)


@parsable.command
def clean(theory):
    '''
    Remove all work for given theory. DANGER
    '''
    print 'Clearing {} Are you sure? [y/N]'.format(theory),
    if raw_input().lower()[:1] == 'y':
        print 'OK, clearing.'
        path = os.path.join(pomagma.util.DATA, 'atlas', theory)
        if os.path.exists(path):
            shutil.rmtree(path)
    else:
        print 'OK, not clearing.'


if __name__ == '__main__':
    signal.signal(signal.SIGINT, raise_keyboard_interrupt)
    sys.argv[0] = 'pomagma'
    parsable.dispatch()
