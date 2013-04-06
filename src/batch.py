import os
import sys
import shutil
import parsable
import pomagma.util
import pomagma.wrapper


parsable_commands = []
def parsable_command(fun):
    parsable_commands.append(fun)
    return fun


@parsable_command
def test(theory):
    '''
    Test basic operations with a given theory:
    init, copy, grow, aggregate
    '''
    buildtype = 'debug' if pomagma.util.debug else 'release'
    data = '{}.{}.test'.format(theory, buildtype)
    data = os.path.join(pomagma.util.DATA, data)
    if os.path.exists(data):
        os.system('rm -f {}/*'.format(data))
    else:
        os.makedirs(data)
    with pomagma.util.chdir(data):

        min_size = pomagma.util.MIN_SIZES[theory]
        dsize = min(512, 1 + min_size)
        sizes = [min_size + i * dsize for i in range(10)]
        opts = dict(log_file='test.log')

        pomagma.wrapper.init(theory, '0.h5', sizes[0], **opts)
        pomagma.wrapper.copy('0.h5', '1.h5', **opts)
        pomagma.wrapper.grow(theory, '1.h5', '2.h5', sizes[1], **opts)
        pomagma.wrapper.trim(theory, '2.h5', '3.h5', sizes[0], **opts)
        pomagma.wrapper.grow(theory, '3.h5', '4.h5', sizes[1], **opts)
        pomagma.wrapper.aggregate('2.h5', '4.h5', '5.h5', **opts)
        pomagma.wrapper.aggregate('5.h5', '0.h5', '6.h5', **opts)
        digest5 = pomagma.util.get_hash('5.h5')
        digest6 = pomagma.util.get_hash('6.h5')
        assert digest5 == digest6


@parsable_command
def init(theory):
    '''
    Init atlas for given theory.
    '''
    data = os.path.join(pomagma.util.DATA, '{}.grow'.format(theory))
    assert not os.path.exists(data), 'Atlas has already been initialized'
    os.makedirs(data)
    with pomagma.util.chdir(data):

        atlas = 'atlas.h5'
        opts = dict(log_file='grow.log')

        print 'Initializing'
        size = pomagma.util.MIN_SIZES[theory]
        pomagma.wrapper.init(theory, atlas, size, **opts)


@parsable_command
def grow(theory, max_size=8191, step_size=512):
    '''
    Work on atlas for given theory.
    Grow atlas until at given size, then (trim; grow; aggregate)-loop
    '''
    # TODO make starting this idempotent, with a mutext or killer or sth
    assert step_size > 0
    seed_size = max_size - step_size
    min_size = pomagma.util.MIN_SIZES[theory]
    assert seed_size >= min_size

    data = os.path.join(pomagma.util.DATA, '{}.grow'.format(theory))
    assert os.path.exists(data), 'First initialize atlas'
    with pomagma.util.chdir(data):

        seed = 'seed.h5'
        chart = 'chart.h5'
        atlas = 'atlas.h5'
        atlas_temp = 'temp.atlas.h5'
        assert os.path.exists(atlas), 'First initialize atlas'
        atlas_size = pomagma.util.get_info(atlas)['item_count']
        opts = dict(log_file='grow.log')

        step = 0
        while atlas_size < max_size:
            atlas_size = min(atlas_size + step_size, max_size)
            print 'Step {}: grow to {}'.format(step, atlas_size)
            pomagma.wrapper.grow(theory, atlas, atlas_temp, atlas_size, **opts)
            pomagma.wrapper.copy(atlas_temp, atlas, **opts) # verifies file
            atlas_size = pomagma.util.get_info(atlas)['item_count']
            print 'atlas_size = {}'.format(atlas_size)
            step += 1

        while True:
            print 'Step {}: trim-grow-aggregate'.format(step)
            pomagma.wrapper.trim(atlas, seed, seed_size, **opts)
            pomagma.wrapper.grow(theory, seed, chart, max_size, **opts)
            pomagma.wrapper.aggregate(atlas, chart, atlas_temp, **opts)
            pomagma.wrapper.copy(atlas_temp, atlas, **opts) # verifies file
            atlas_size = pomagma.util.get_info(atlas)['item_count']
            print 'atlas_size = {}'.format(atlas_size)
            step += 1


@parsable_command
def clean(theory):
    '''
    Remove all work for given theory. DANGER
    '''
    print 'Are you sure? [Y/n]',
    if raw_input().lower()[:1] == 'y':
        data = os.path.join(pomagma.util.DATA, '{}.grow'.format(theory))
        if os.path.exists(data):
            shutil.rmtree(data)


if __name__ == '__main__':
    map(parsable.command, parsable_commands)
    parsable.dispatch()
