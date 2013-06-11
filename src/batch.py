import os
import shutil
import parsable
parsable = parsable.Parsable()
import pomagma.util
import pomagma.surveyor
import pomagma.cartographer
import pomagma.theorist


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
        dsize = min(512, 1 + min_size)
        sizes = [min_size + i * dsize for i in range(10)]
        opts = options
        opts.setdefault('log_file', 'test.log')

        pomagma.surveyor.init(theory, '0.h5', sizes[0], **opts)
        pomagma.cartographer.validate('0.h5', **opts)
        pomagma.cartographer.copy('0.h5', '1.h5', **opts)
        pomagma.surveyor.survey(theory, '1.h5', '2.h5', sizes[1], **opts)
        pomagma.cartographer.trim(theory, '2.h5', '3.h5', sizes[0], **opts)
        pomagma.surveyor.survey(theory, '3.h5', '4.h5', sizes[1], **opts)
        pomagma.cartographer.aggregate('2.h5', '4.h5', '5.h5', **opts)
        pomagma.cartographer.aggregate('5.h5', '0.h5', '6.h5', **opts)
        pomagma.theorist.conjecture_diverge(
            theory,
            '6.h5',
            'diverge.conjectures',
            **opts)
        pomagma.theorist.conjecture_equal(
            theory,
            '6.h5',
            'equal.conjectures',
            **opts)
        # TODO test pomagma.theorist.assume here
        digest5 = pomagma.util.get_hash('5.h5')
        digest6 = pomagma.util.get_hash('6.h5')
        assert digest5 == digest6


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
        opts.setdefault('log_file', 'init.log')

        def log_print(message):
            pomagma.util.log_print(message, opts['log_file'])

        world_size = pomagma.util.MIN_SIZES[theory]
        log_print('Step 0: initialize to {}'.format(world_size))
        pomagma.surveyor.init(theory, survey, world_size, **opts)
        with pomagma.util.mutex():
            pomagma.cartographer.validate(theory, survey, **opts)
            assert not os.path.exists(world), 'already initialized'
            os.rename(survey, world)


@parsable.command
def survey(theory, max_size=8191, step_size=512, **options):
    '''
    Expand world map for given theory.
    Survey until world reaches given size, then (trim; survey; aggregate)-loop
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
        region = '{}.trim.h5'.format(os.getpid())
        survey = '{}.survey.h5'.format(os.getpid())
        aggregate = '{}.aggregate.h5'.format(os.getpid())
        assert os.path.exists(world), 'First initialize world map'
        opts = options
        opts.setdefault('log_file', 'survey.log')

        def log_print(message):
            pomagma.util.log_print(message, opts['log_file'])

        step = 1
        while True:
            log_print('Step {}'.format(step))

            region_size = max(min_size, max_size - step_size)
            pomagma.cartographer.trim(
                theory,
                world,
                region,
                region_size,
                **opts)
            region_size = pomagma.util.get_info(region)['item_count']
            survey_size = min(region_size + step_size, max_size)
            pomagma.surveyor.survey(
                theory,
                region,
                survey,
                survey_size,
                **opts)
            os.remove(region)

            with pomagma.util.mutex():
                pomagma.cartographer.aggregate(
                    world,
                    survey,
                    aggregate,
                    **opts)
                pomagma.cartographer.validate(aggregate, **opts)
                os.rename(aggregate, world)
            os.remove(survey)

            world_size = pomagma.util.get_info(world)['item_count']
            log_print('world_size = {}'.format(world_size))
            step += 1


@parsable.command
def theorize(theory, **options):
    '''
    Make conjectures based on atlas and update atlas based on theorems.
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First build world map'
    with pomagma.util.chdir(path):

        world = 'world.h5'
        assume = '{}.assume.h5'.format(os.getpid())
        conjectures = 'conjecture_diverge.terms'
        theorems = 'filter_diverge.facts'
        assert os.path.exists(world), 'First build world map'
        opts = options
        opts.setdefault('log_file', 'conjecture.log')
        pomagma.theorist.conjecture_diverge(theory, world, conjectures, **opts)
        pomagma.theorist.filter_diverge(conjectures, theorems, **opts)
        pomagma.theorist.assume(world, assume, theorems, **opts)
        with pomagma.util.mutex():
            pomagma.cartographer.validate(assume, **opts)
            os.rename(assume, world)


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
        opts.setdefault('log_level', 2)
        region = 'region.{:d}.h5'.format(size)
        temp = '{}.profile.h5'.format(os.getpid())
        world = 'world.h5'

        if not os.path.exists(region):
            assert os.path.exists(world), 'First initialize world map'
            pomagma.cartographer.trim(theory, world, region, size, **opts)
        opts.setdefault('runner', 'valgrind --tool=callgrind')
        pomagma.surveyor.survey(theory, region, temp, size + dsize, **opts)


def sparse_range(min_size, max_size):
    sizes = [512]
    while True:
        size = 2 * sizes[-1]
        if size <= max_size:
            sizes.append(size)
        else:
            break
    sizes += [3 * size for size in sizes if 3 * size < max_size]
    sizes = [size - 1 for size in sizes if size > min_size]
    sizes.sort()
    return sizes


@parsable.command
def trim_regions(theory='skj', **opts):
    '''
    Trim a set of regions for testing on small machines.
    '''
    path = os.path.join(pomagma.util.DATA, 'atlas', theory)
    assert os.path.exists(path), 'First initialize world map'
    with pomagma.util.chdir(path):
        world = 'world.h5'
        min_size = pomagma.util.MIN_SIZES[theory]
        max_size = pomagma.util.get_info(world)['item_count']
        sizes = reversed(sparse_range(min_size, max_size))
        larger = world
        for size in sizes:
            print 'Trimming region of size', size
            smaller = 'region.{:d}.h5'.format(size)
            pomagma.cartographer.trim(theory, larger, smaller, size, **opts)
            larger = smaller
        pomagma.cartographer.validate(larger, **opts)


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
    print 'Are you sure? [Y/n]',
    if raw_input().lower()[:1] == 'y':
        path = os.path.join(pomagma.util.DATA, 'atlas', theory)
        if os.path.exists(path):
            shutil.rmtree(path)


if __name__ == '__main__':
    parsable.dispatch()
