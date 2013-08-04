import os
import sys
import shutil
import subprocess
import parsable
parsable = parsable.Parsable()
import pomagma.util
from pomagma import surveyor, cartographer, theorist, analyst, atlas


DEFAULT_SURVEY_SIZE = 16384 + 512 - 1
PYTHON = sys.executable


class parsable_fork:
    def __init__(self, fun, *args, **kwargs):
        self.args = [PYTHON, '-m', 'pomagma.batch', fun.__name__]
        self.args += map(str, args)
        for key, val in kwargs.iteritems():
            self.args.append('{}={}'.format(key, val))
        self.proc = subprocess.Popen(self.args)

    def wait(self):
        self.proc.wait()
        code = self.proc.returncode
        assert code == 0, '\n'.join([
            'forked command failed with exit code {}'.format(code),
            ' '.join(self.args)])


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
        opts = options
        opts.setdefault('log_file', 'test.log')
        theorems = 'theorems.facts'
        conjectures = 'conjectures.facts'
        simplified = 'simplified.facts'

        surveyor.init(theory, '0.h5', sizes[0], **opts)
        cartographer.validate('0.h5', **opts)
        cartographer.copy('0.h5', '1.h5', **opts)
        surveyor.survey(theory, '1.h5', '2.h5', sizes[1], **opts)
        cartographer.trim(theory, '2.h5', '3.h5', sizes[0], **opts)
        surveyor.survey(theory, '3.h5', '4.h5', sizes[1], **opts)
        cartographer.aggregate('2.h5', '4.h5', '5.h5', **opts)
        cartographer.aggregate('5.h5', '0.h5', '6.h5', **opts)
        digest5 = pomagma.util.get_hash('5.h5')
        digest6 = pomagma.util.get_hash('6.h5')
        assert digest5 == digest6

        theorist.conjecture_diverge(theory, '6.h5', conjectures, **opts)
        if theory != 'h4':
            theorist.try_prove_diverge(
                conjectures,
                conjectures,
                theorems,
                **opts)
            theorist.assume('6.h5', '7.h5', theorems, **opts)
            cartographer.validate('7.h5', **opts)
        theorist.conjecture_equal(theory, '6.h5', conjectures, **opts)
        theorist.try_prove_nless(
            theory,
            '6.h5',
            conjectures,
            conjectures,
            theorems,
            **opts)
        if theory != 'h4':
            theorist.assume('6.h5', '7.h5', theorems, **opts)
            cartographer.validate('7.h5', **opts)
            cartographer.infer('7.h5', '8.h5', **opts)

        analyst.simplify(theory, '6.h5', conjectures, simplified, **opts)


@parsable.command
def init(theory, **options):
    '''
    Initialize world map for given theory.
    Options: log_level, log_file
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert not os.path.exists(path), 'World map has already been initialized'
    os.makedirs(path)
    with pomagma.util.chdir(path):
        world = 'world.h5'
        survey = '{}.survey.h5'.format(os.getpid())
        opts = options
        log_file = opts.setdefault('log_file', 'init.log')
        world_size = pomagma.util.MIN_SIZES[theory]
        pomagma.util.log_print('initialize to {}'.format(world_size), log_file)
        surveyor.init(theory, survey, world_size, **opts)
        atlas.initialize(world, survey, **opts)


@parsable.command
def infer(theory, **options):
    '''
    Infer simple facts in the world map.
    Options: log_level, log_file
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First initialize world map'
    with pomagma.util.chdir(path):
        world = 'world.h5'
        assert os.path.exists(world), 'First initialize world map'
        updated = '{}.infer.h5'.format(os.getpid())
        opts = options
        opts.setdefault('log_file', 'infer.log')
        atlas.infer(world, updated, **opts)


@parsable.command
def survey(theory, max_size=DEFAULT_SURVEY_SIZE, step_size=512, **options):
    '''
    Expand world map for given theory.
    Survey one step in the (trim; survey; aggregate)-loop.
    Options: log_level, log_file
    '''
    assert step_size > 0
    region_size = max_size - step_size
    min_size = pomagma.util.MIN_SIZES[theory]
    assert region_size >= min_size
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First initialize world map'
    with pomagma.util.chdir(path):
        world = 'world.h5'
        assert os.path.exists(world), 'First initialize world map'
        region = '{}.trim.h5'.format(os.getpid())
        survey = '{}.survey.h5'.format(os.getpid())
        aggregate = '{}.aggregate.h5'.format(os.getpid())
        opts = options
        log_file = opts.setdefault('log_file', 'survey.log')
        # TODO split this up into separate survey + aggregate actors
        #   surveyors pull from s3 and aggregators push to s3
        region_size = max(min_size, max_size - step_size)
        cartographer.trim(theory, world, region, region_size, **opts)
        region_size = pomagma.util.get_item_count(region)
        survey_size = min(region_size + step_size, max_size)
        surveyor.survey(theory, region, survey, survey_size, **opts)
        os.remove(region)
        atlas.aggregate(world, survey, aggregate, **opts)
        world_size = pomagma.util.get_item_count(world)
        pomagma.util.log_print('world_size = {}'.format(world_size), log_file)


@parsable.command
def explore(theory, max_size=DEFAULT_SURVEY_SIZE, step_size=512, **options):
    '''
    Continuously expand world map for given theory, inferring and surveying.
    Survey until world reaches given size, then (trim; survey; aggregate)-loop.
    Options: log_level, log_file
    '''
    while True:
        workers = [
            parsable_fork(infer, theory, **options),
            parsable_fork(survey, theory, max_size, step_size, **options),
        ]
        for worker in workers:
            worker.wait()


@parsable.command
def extend(theory, **options):
    '''
    Extend language of world map (only needed when language changes).
    Options: log_level, log_file
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First initialize world map'
    with pomagma.util.chdir(path):
        world = 'world.h5'
        init = '{}.init.h5'.format(os.getpid())
        aggregate = '{}.aggregate.h5'.format(os.getpid())
        assert os.path.exists(world), 'First initialize world map'
        opts = options
        opts.setdefault('log_file', 'extend.log')
        init_size = pomagma.util.MIN_SIZES[theory]
        surveyor.init(theory, init, init_size, **opts)
        atlas.aggregate(world, init, aggregate, **opts)


@parsable.command
def theorize(theory, **options):
    '''
    Make conjectures based on atlas and update atlas based on theorems.
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First build world map'
    with pomagma.util.chdir(path):

        world = 'world.h5'
        updated = '{}.assume.h5'.format(os.getpid())
        temp_conjectures = '{}.conjectures.facts'.format(os.getpid())
        diverge_conjectures = 'diverge_conjectures.facts'
        diverge_theorems = 'diverge_theorems.facts'
        equal_conjectures = 'equal_conjectures.facts'
        nless_theorems = 'nless_theorems.facts'
        assert os.path.exists(world), 'First build world map'
        opts = options
        opts.setdefault('log_file', 'theorize.log')

        theorist.conjecture_diverge(theory, world, diverge_conjectures, **opts)
        theorem_count = theorist.try_prove_diverge(
            diverge_conjectures,
            temp_conjectures,
            diverge_theorems,
            **opts)
        os.rename(temp_conjectures, diverge_conjectures)
        if theorem_count > 0:
            atlas.assume(world, updated, diverge_theorems, **opts)

        theorem_count = theorist.try_prove_nless(
            theory,
            world,
            equal_conjectures,
            temp_conjectures,
            nless_theorems,
            **opts)
        os.rename(temp_conjectures, equal_conjectures)
        if theorem_count > 0:
            atlas.assume(world, updated, nless_theorems, **opts)


@parsable.command
def profile(theory='skj', size_blocks=3, dsize_blocks=0, **options):
    '''
    Profile surveyor through callgrind on random region of world.
    Inputs: theory, region size in blocks (1 block = 512 obs)
    Options: log_level, log_file
    '''
    size = size_blocks * 512 - 1
    dsize = dsize_blocks * 512
    min_size = pomagma.util.MIN_SIZES[theory]
    assert size >= min_size

    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First initialize world map'
    with pomagma.util.chdir(path):

        opts = options
        opts.setdefault('log_file', 'profile.log')
        region = 'region.{:d}.h5'.format(size)
        temp = '{}.profile.h5'.format(os.getpid())
        world = 'world.h5'

        if not os.path.exists(region):
            assert os.path.exists(world), 'First initialize world map'
            cartographer.trim(theory, world, region, size, **opts)
        opts.setdefault('runner', 'valgrind --tool=callgrind')
        surveyor.survey(theory, region, temp, size + dsize, **opts)


def sparse_range(min_size, max_size):
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
def trim_regions(theory='skj', **options):
    '''
    Trim a set of regions for testing on small machines.
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First initialize world map'
    with pomagma.util.chdir(path):

        opts = options
        opts.setdefault('log_file', 'trim_regions.log')
        world = 'world.h5'
        min_size = pomagma.util.MIN_SIZES[theory]
        max_size = pomagma.util.get_item_count(world)
        sizes = reversed(sparse_range(min_size, max_size))
        larger = world
        for size in sizes:
            print 'Trimming region of size', size
            smaller = 'region.{:d}.h5'.format(size)
            cartographer.trim(theory, larger, smaller, size, **opts)
            larger = smaller
        cartographer.validate(larger, **opts)


@parsable.command
def make(theory, max_size=8191, step_size=512, **options):
    '''
    Initialize; survey.
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    if not os.path.exists(path):
        init(theory, **options)
    survey(theory, max_size, step_size, **options)


@parsable.command
def clean(theory):
    '''
    Remove all work for given theory. DANGER
    '''
    print 'Clearing {} Are you sure? [Y/n]'.format(theory),
    if raw_input().lower()[:1] == 'y':
        path = os.path.join(pomagma.util.DATA, 'atlas', theory)
        if os.path.exists(path):
            shutil.rmtree(path)


if __name__ == '__main__':
    parsable.dispatch()
