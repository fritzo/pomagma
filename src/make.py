import os
import glob
import parsable
import pomagma.util
from pomagma import atlas, surveyor, cartographer, theorist, analyst


def _test_atlas(theory):
    '''
    Test basic operations in one theory:
        init, validate, copy, survey, aggregate,
        conjecture_diverge, conjecture_equal
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
        opts = {'log_file': 'test.log', 'log_level': 2}
        diverge_conjectures = 'diverge_conjectures.facts'
        diverge_theorems = 'diverge_theorems.facts'
        equal_conjectures = 'equal_conjectures.facts'
        equal_theorems = 'equal_theorems.facts'

        surveyor.init(theory, '0.h5', sizes[0], **opts)
        with cartographer.load(theory, '0.h5', **opts) as db:
            db.validate()
            db.dump('1.h5')
            expected_size = pomagma.util.get_item_count('1.h5')
            actual_size = db.info()['item_count']
            assert actual_size == expected_size
        surveyor.survey(theory, '1.h5', '2.h5', sizes[1], **opts)
        with cartographer.load(theory, '2.h5', **opts) as db:
            db.trim([{'size': sizes[0], 'filename': '3.h5'}])
        surveyor.survey(theory, '3.h5', '4.h5', sizes[1], **opts)
        with cartographer.load(theory, '2.h5', **opts) as db:
            db.aggregate('4.h5')
            db.dump('5.h5')
        with cartographer.load(theory, '5.h5', **opts) as db:
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
                    **opts)
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
            **opts)
        # assert theorem_count > 0, theorem_count

        if theory != 'h4':
            with cartographer.load(theory, '6.h5', **opts) as db:
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
            with analyst.load(theory, '7.h5', **opts) as db:
                fail_count = db.test_inference()
                assert fail_count == 0, 'analyst.test_inference failed'


@parsable.command
def test_atlas(theory='all'):
    '''
    Test atlas exploration and analysis operations.
    '''
    if theory == 'all':
        theories = pomagma.util.MIN_SIZES.keys()
        theories.sort(key=pomagma.util.MIN_SIZES.__getitem__)
    else:
        theories = [theory]

    for theory in theories:
        print '-' * 78
        print 'Testing', theory
        _test_atlas(theory)


@parsable.command
def test_analyst(theory):
    '''
    Test analyst approximation on normalized world map.
    '''
    opts = {'log_file': 'test.log', 'log_level': 2}
    with atlas.chdir(theory):
        world = 'world.normal.h5'
        assert os.path.exists(world), 'First initialize normalized world'
        with analyst.load(theory, world, **opts) as db:
            fail_count = db.test()
    assert fail_count == 0, 'Failed {} cases'.format(fail_count)
    print 'Passed analyst test'


@parsable.command
def profile_util():
    '''
    Profile data structures.
    '''
    buildtype = 'debug' if pomagma.util.debug else 'release'
    log_file = os.path.join(pomagma.util.DATA, 'profile', buildtype + '.log')
    if os.path.exists(log_file):
        os.remove(log_file)
    opts = {'log_file': log_file, 'log_level': 2}
    pattern = os.path.join(pomagma.util.BIN, '*', '*_profile')
    cmds = glob.glob(pattern)
    assert cmds, 'no profiles match {}'.format(pattern)
    for cmd in cmds:
        print 'Profiling', cmd
        pomagma.util.log_call(cmd, **opts)
    pomagma.util.check_call('cat', log_file)


@parsable.command
def profile_surveyor(theory, size_blocks=3, dsize_blocks=0):
    '''
    Profile surveyor through callgrind on random region of world.
    Inputs: theory, region size in blocks (1 block = 512 obs)
    '''
    size = size_blocks * 512 - 1
    dsize = dsize_blocks * 512
    min_size = pomagma.util.MIN_SIZES[theory]
    assert size >= min_size
    with atlas.chdir(theory):
        opts = {'log_file': 'profile.log', 'log_level': 2}
        region = 'region.{:d}.h5'.format(size)
        temp = pomagma.util.temp_name('profile.h5')
        world = 'world.h5'

        if not os.path.exists(region):
            assert os.path.exists(world), 'First initialize world map'
            with cartographer.load(theory, world, **opts) as db:
                db.trim({'size': size, 'filename': region})
        opts.setdefault('runner', 'valgrind --tool=callgrind')
        surveyor.survey(theory, region, temp, size + dsize, **opts)
        os.remove(temp)


@parsable.command
def coverity():
    '''
    Check pomagma build with coverity. (see http://coverity.com)
    '''
    pomagma.util.coverity()


if __name__ == '__main__':
    parsable.dispatch()
