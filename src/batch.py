import os
import shutil
import parsable; parsable = parsable.Parsable()
import pomagma.util
import pomagma.actions


@parsable.command
def test(laws, **options):
    '''
    Test basic operations in one laws: init, copy, survey, aggregate
    Options: log_level, log_file
    '''
    buildtype = 'debug' if pomagma.util.debug else 'release'
    data = '{}.{}.test'.format(laws, buildtype)
    data = os.path.join(pomagma.util.DATA, data)
    if os.path.exists(data):
        os.system('rm -f {}/*'.format(data))
    else:
        os.makedirs(data)
    with pomagma.util.chdir(data), pomagma.util.mutex(block=False):

        min_size = pomagma.util.MIN_SIZES[laws]
        dsize = min(512, 1 + min_size)
        sizes = [min_size + i * dsize for i in range(10)]
        opts = options
        opts.setdefault('log_file', 'test.log')

        pomagma.actions.init(laws, '0.h5', sizes[0], **opts)
        pomagma.actions.copy('0.h5', '1.h5', **opts)
        pomagma.actions.survey(laws, '1.h5', '2.h5', sizes[1], **opts)
        pomagma.actions.trim(laws, '2.h5', '3.h5', sizes[0], **opts)
        pomagma.actions.survey(laws, '3.h5', '4.h5', sizes[1], **opts)
        pomagma.actions.aggregate('2.h5', '4.h5', '5.h5', **opts)
        pomagma.actions.aggregate('5.h5', '0.h5', '6.h5', **opts)
        digest5 = pomagma.util.get_hash('5.h5')
        digest6 = pomagma.util.get_hash('6.h5')
        assert digest5 == digest6


@parsable.command
def init(laws, **options):
    '''
    Initialize world map for given laws.
    Options: log_level, log_file
    '''
    data = os.path.join(pomagma.util.DATA, '{}.survey'.format(laws))
    assert not os.path.exists(data), 'World map has already been initialized'
    os.makedirs(data)
    with pomagma.util.chdir(data), pomagma.util.mutex(block=False):

        world = 'world.h5'
        opts = options
        opts.setdefault('log_file', 'survey.log')
        def log_print(message):
            pomagma.util.log_print(message, opts['log_file'])

        world_size = pomagma.util.MIN_SIZES[laws]
        log_print('Step 0: initialize to {}'.format(world_size))
        pomagma.actions.init(laws, world, world_size, **opts)


@parsable.command
def survey(laws, max_size=8191, step_size=512, **options):
    '''
    Expand world map for given laws.
    Survey until world reaches given size, then (trim; survey; aggregate)-loop
    Options: log_level, log_file
    '''
    assert step_size > 0
    region_size = max_size - step_size
    min_size = pomagma.util.MIN_SIZES[laws]
    assert region_size >= min_size

    data = os.path.join(pomagma.util.DATA, '{}.survey'.format(laws))
    assert os.path.exists(data), 'First initialize world map'
    with pomagma.util.chdir(data), pomagma.util.mutex(block=False):

        world = 'world.h5'
        region = 'region.h5'
        survey = 'survey.h5'
        temp = 'temp.world.h5'
        assert os.path.exists(world), 'First initialize world map'
        world_size = pomagma.util.get_info(world)['item_count']
        opts = options
        opts.setdefault('log_file', 'survey.log')
        def log_print(message):
            pomagma.util.log_print(message, opts['log_file'])

        step = 1
        while True:

            if world_size < max_size:
                world_size = min(world_size + step_size, max_size)
                log_print('Step {}: survey to {}'.format(step, world_size))
                pomagma.actions.survey(laws, world, temp, world_size, **opts)
                pomagma.actions.copy(temp, world, **opts) # verifies file

            else:
                log_print('Step {}: trim-survey-aggregate'.format(step))
                pomagma.actions.trim(laws, world, region, region_size, **opts)
                pomagma.actions.survey(laws, region, survey, max_size, **opts)
                pomagma.actions.aggregate(world, survey, temp, **opts)
                pomagma.actions.copy(temp, world, **opts) # verifies file

            world_size = pomagma.util.get_info(world)['item_count']
            log_print('world_size = {}'.format(world_size))
            step += 1


@parsable.command
def profile(laws='skj', size_blocks=3, dsize_blocks=0, **options):
    '''
    Profile surveyor through callgrind on random region of world.
    Inputs: laws, region size in blocks (1 block = 512 obs)
    Options: log_level, log_file
    '''
    size = size_blocks * 512 - 1
    dsize = dsize_blocks * 512
    min_size = pomagma.util.MIN_SIZES[laws]
    assert size >= min_size

    data = os.path.join(pomagma.util.DATA, '{}.survey'.format(laws))
    assert os.path.exists(data), 'First initialize world map'
    with pomagma.util.chdir(data):

        opts = options
        opts.setdefault('log_file', 'profile.log')
        region = 'region.{:d}.h5'.format(size)
        temp = 'temp.profile.h5'.format(size + 1)
        world = 'world.h5'

        if not os.path.exists(region):
            assert os.path.exists(world), 'First initialize world map'
            pomagma.actions.trim(laws, world, region, size, **opts)
        opts.setdefault('runner', 'valgrind --tool=callgrind')
        pomagma.actions.survey(laws, region, temp, size + dsize, **opts)


@parsable.command
def make(laws, max_size=8191, step_size=512, **options):
    '''
    Initialize; survey.
    '''
    data = os.path.join(pomagma.util.DATA, '{}.survey'.format(laws))
    if not os.path.exists(data):
        init(laws, **options)
    survey(laws, max_size, step_size, **options)


@parsable.command
def clean(laws):
    '''
    Remove all work for given laws. DANGER
    '''
    print 'Are you sure? [Y/n]',
    if raw_input().lower()[:1] == 'y':
        data = os.path.join(pomagma.util.DATA, '{}.survey'.format(laws))
        if os.path.exists(data):
            shutil.rmtree(data)


if __name__ == '__main__':
    parsable.dispatch()
