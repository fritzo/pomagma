import os
import shutil
import parsable
parsable = parsable.Parsable()
import pomagma.util
import pomagma.workers
from pomagma import surveyor, cartographer, theorist, analyst, atlas


@parsable.command
def test(theory, **options):
    '''
    Test basic operations in one theory:
        init, validate, copy, survey, aggregate,
        conjecture_diverge, conjecture_equal
    Options: log_level, log_file
    '''
    buildtype = 'debug' if pomagma.util.debug else 'release'
    path = os.path.join(pomagma.util.DATA, 'test', buildtype, 'atlas', theory)
    if os.path.exists(path):
        os.system('rm -f {}/*'.format(path))
    else:
        os.makedirs(path)
    with pomagma.util.chdir(path), pomagma.util.mutex(block=False):

        min_size = pomagma.util.MIN_SIZES[theory]
        dsize = min(64, 1 + min_size)
        sizes = [min_size + i * dsize for i in range(10)]
        options.setdefault('log_file', 'test.log')
        diverge_conjectures = 'diverge_conjectures.facts'
        diverge_theorems = 'diverge_theorems.facts'
        equal_conjectures = 'equal_conjectures.facts'
        equal_theorems = 'equal_theorems.facts'
        simplified = 'simplified.facts'

        surveyor.init(theory, '0.h5', sizes[0], **options)
        with cartographer.load(theory, '0.h5', **options) as db:
            db.validate()
            db.dump('1.h5')
            expected_size = pomagma.util.get_item_count('1.h5')
            actual_size = db.info()['item_count']
            assert actual_size == expected_size
        surveyor.survey(theory, '1.h5', '2.h5', sizes[1], **options)
        with cartographer.load(theory, '2.h5', **options) as db:
            db.trim([{'size': sizes[0], 'filename': '3.h5'}])
        surveyor.survey(theory, '3.h5', '4.h5', sizes[1], **options)
        with cartographer.load(theory, '2.h5', **options) as db:
            db.aggregate('4.h5')
            db.dump('5.h5')
        with cartographer.load(theory, '5.h5', **options) as db:
            db.aggregate('0.h5')
            db.dump('6.h5')
            digest5 = pomagma.util.get_hash('5.h5')
            digest6 = pomagma.util.get_hash('6.h5')
            assert digest5 == digest6

            counts = db.conjecture(diverge_conjectures, equal_conjectures)
            assert counts['diverge_count'] > 0, counts['diverge_count']
            assert counts['equal_count'] > 0, counts['equal_count']
            if theory != 'h4':
                theorem_count = theorist.try_prove_diverge(
                    diverge_conjectures,
                    diverge_conjectures,
                    diverge_theorems,
                    **options)
                assert theorem_count > 0, theorem_count
                counts = db.assume(diverge_theorems)
                assert counts['pos'] + counts['neg'] > 0, counts
                db.validate()
                db.dump('6.h5')
        theorem_count = theorist.try_prove_nless(
            theory,
            '6.h5',
            equal_conjectures,
            equal_conjectures,
            equal_theorems,
            **options)
        #assert theorem_count > 0, theorem_count

        def test_analyst_validate(db, examples):
            expected = examples.values()
            actual = db.validate(examples.keys())
            for a, e in zip(actual, expected):
                assert a == e, 'analyst.validate, {} vs {}'.format(a, e)

        if theory == 'h4':
            with analyst.load(theory, '6.h5', **options) as db:
                line_count = db.batch_simplify(equal_theorems, simplified)
                assert line_count > 0, line_count
                test_analyst_validate(db, {
                    'BOT': {'is_top': False, 'is_bot': True},
                    'TOP': {'is_top': True, 'is_bot': False},
                })
        else:
            with cartographer.load(theory, '6.h5', **options) as db:
                db.assume(equal_theorems)
                if theorem_count > 0:
                    assert counts['merge'] > 0, counts
                db.validate()
                for priority in [0, 1]:
                    while db.infer(priority):
                        db.validate()
                for priority in [0, 1]:
                    assert not db.infer(priority)
                db.dump('7.h5')
            with analyst.load(theory, '7.h5', **options) as db:
                line_count = db.batch_simplify(diverge_theorems, simplified)
                assert line_count > 0, line_count
                fail_count = db.test()
                assert fail_count == 0, 'analyst.batch_simplify failed'
                test_analyst_validate(db, {
                    'BOT': {'is_top': False, 'is_bot': True},
                    'TOP': {'is_top': True, 'is_bot': False},
                    'I': {'is_top': False, 'is_bot': False},
                    'APP I I': {'is_top': False, 'is_bot': False},
                    'COMP I I': {'is_top': False, 'is_bot': False},
                })


@parsable.command
def init(theory, **options):
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
        with pomagma.util.temp_copy(survey) as temp:
            surveyor.init(theory, temp, world_size, **options)
        with atlas.load(theory, survey, **options) as db:
            assert not os.path.exists(world), world
            db.validate()
            db.dump(world)


@parsable.command
def explore(
        theory,
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
def make(theory, max_size=8191, step_size=512, **options):
    '''
    Initialize; explore.
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    if not os.path.exists(path):
        init(theory, **options)
    explore(theory, max_size, step_size, **options)


@parsable.command
def translate(theory, **options):
    '''
    Translate language of world map (e.g. when language changes).
    Options: log_level, log_file
    '''
    with atlas.chdir(theory):
        world = 'world.h5'
        init = pomagma.util.temp_name('init.h5')
        aggregate = pomagma.util.temp_name('aggregate.h5')
        assert os.path.exists(world), 'First initialize world map'
        options.setdefault('log_file', 'translate.log')
        init_size = pomagma.util.MIN_SIZES[theory]
        surveyor.init(theory, init, init_size, **options)
        atlas.translate(theory, init, world, aggregate, **options)


@parsable.command
def theorize(theory, **options):
    '''
    Make conjectures based on atlas and update atlas based on theorems.
    '''
    with atlas.chdir(theory):
        world = 'world.h5'
        diverge_conjectures = 'diverge_conjectures.facts'
        diverge_theorems = 'diverge_theorems.facts'
        equal_conjectures = 'equal_conjectures.facts'
        nless_theorems = 'nless_theorems.facts'
        assert os.path.exists(world), 'First build world map'
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
def trim(theory, parallel=True, **options):
    '''
    Trim a set of normal regions for running analyst on small machines.
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


@parsable.command
def analyze(theory, size=None, address=analyst.ADDRESS, **options):
    '''
    Run analyst server on normalized world map.
    '''
    with atlas.chdir(theory):
        options.setdefault('log_file', 'analyst.log')
        if size is None:
            world = 'world.normal.h5'
        else:
            world = 'region.normal.{}.h5'.format(size)
        assert os.path.exists(world), 'First initialize normalized world'
        try:
            server = analyst.serve(theory, world, **options)
            server.wait()
        finally:
            server.stop()


@parsable.command
def test_analyst(theory, **options):
    '''
    Test analyst approximation on normalized world map.
    '''
    options.setdefault('log_file', 'test.log')
    with atlas.chdir(theory):
        world = 'world.normal.h5'
        assert os.path.exists(world), 'First initialize normalized world'
        with analyst.load(theory, world, **options) as db:
            fail_count = db.test()
    assert fail_count == 0, 'Failed {} cases'.format(fail_count)
    print 'Passed analyst test'


@parsable.command
def profile_surveyor(theory, size_blocks=3, dsize_blocks=0, **options):
    '''
    Profile surveyor through callgrind on random region of world.
    Inputs: theory, region size in blocks (1 block = 512 obs)
    Options: log_level, log_file
    '''
    size = size_blocks * 512 - 1
    dsize = dsize_blocks * 512
    min_size = pomagma.util.MIN_SIZES[theory]
    assert size >= min_size
    with atlas.chdir(theory):
        options.setdefault('log_file', 'profile.log')
        region = 'region.{:d}.h5'.format(size)
        temp = pomagma.util.temp_name('profile.h5')
        world = 'world.h5'

        if not os.path.exists(region):
            assert os.path.exists(world), 'First initialize world map'
            with cartographer.load(theory, world, **options) as db:
                db.trim({'size': size, 'filename': region})
        options.setdefault('runner', 'valgrind --tool=callgrind')
        surveyor.survey(theory, region, temp, size + dsize, **options)
        os.remove(temp)


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
    parsable.dispatch()
