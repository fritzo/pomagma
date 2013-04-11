'''
Activities for grow workflow.

References:
http://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-using-swf-api.html#swf-dg-error-handling
'''

import os
import shutil
import simplejson as json
import parsable
import pomagma.util
import pomagma.store
import pomagma.actions
import pomagma.workflow.swf


STEP_SIZE = 512

reproducible = pomagma.workflow.swf.reproducible('pomagma.workflow.grow')


def random_filename():
    return 'temp/{}.h5'.format(pomagma.util.random_uuid())


def normalize_filename(prefix, old_filename):
    hash_ = pomagma.util.get_hash(old_filename)
    new_filename = '{}/{}.h5'.format(prefix, hash_)
    os.rename(old_filename, new_filename)
    return new_filename


def get_size(filename):
    return pomagma.util.get_info(filename)['item_count']


@reproducible
def trim(task):
    args = json.loads(task['input'])
    theory = args['theory']
    size = args['size']
    min_size = pomagma.util.MIN_SIZES[theory]
    seed_size = max(min_size, size - STEP_SIZE)
    atlas = pomagma.store.get('{}/atlas.h5'.format(theory))
    atlas_size = get_size(atlas)
    if seed_size < atlas_size:
        seed = random_filename()
        log_file = '{}/grow.log'.format(theory)
        pomagma.actions.trim(theory, atlas, seed, size, log_file=log_file)
    else:
        seed = atlas
    seed = normalize_filename('{}/seed'.format(theory), seed)
    pomagma.store.put(seed)
    return {
        'nextActivity': {
            'activityType': '{}_{}_{}'.format('Grow', theory, size),
            'input': {
                'theory': theory,
                'size': size,
                'seedFile': seed,
                },
            }
        }


@reproducible
def grow(task):
    args = json.loads(task['input'])
    theory = args['theory']
    size = args['size']
    seed = args['seedFile']
    seed = pomagma.store.get(seed)
    seed_size = get_size(seed)
    chart_size = min(size, seed_size + STEP_SIZE)
    chart = random_filename()
    log_file = '{}/grow.log'.format(theory)
    pomagma.actions.grow(theory, seed, chart, chart_size, log_file=log_file)
    chart = normalize_filename('{}/chart'.format(theory), chart)
    pomagma.store.put(chart)
    pomagma.store.remove(seed)
    return {
        'nextActivity': {
            'activityType': '{}_{}'.format('Aggregate', theory),
            'input': {
                'theory': theory,
                'size': size,
                'chartFile': chart,
                },
            }
        }


@reproducible
def aggregate(task):
    args = json.loads(task['input'])
    theory = args['theory']
    chart = args['chartFile']
    atlas = pomagma.store.get('{}/atlas.h5'.format(theory))
    chart = pomagma.store.get(chart)
    log_file = '{}/grow.log'.format(theory)
    pomagma.actions.aggregate(atlas, chart, atlas, log_file=log_file)
    pomagma.store.put(atlas)
    pomagma.store.remove(chart)


@parsable.command
def start_trimmer():
    '''
    Start trimmer, typically on a high-memory node.
    '''
    name = 'Trim'
    pomagma.workflow.swf.register_activity_type(name)
    while True:
        task = pomagma.workflow.swf.poll_activity_task(name)
        trim(task)


@parsable.command
def start_aggregator(theory):
    '''
    Start aggregator, typically on a high-memory node.
    WARNING There must be exactly one aggregator per theory.
    '''
    name = '{}_{}'.format('Aggregate', theory)
    pomagma.workflow.swf.register_activity_type(name)
    while True:
        task = pomagma.workflow.swf.poll_activity_task(name)
        aggregate(task)


@parsable.command
def start_grower(theory, size):
    '''
    Start grow worker, typically on a high-memory high-cpu node.
    '''
    workflow_name = 'Grow'
    name = '{}_{}_{}'.format('Grow', theory, size)
    param = json.dumps({'theory': theory, 'size': size})
    pomagma.workflow.swf.register_activity_type(name)
    pomagma.workflow.swf.register_workflow_type(workflow_name)
    while True:
        workflow_id = pomagma.util.random_uuid()
        pomagma.workflow.swf.start_workflow_execution(
                workflow_id,
                workflow_name,
                param)
        task = pomagma.workflow.swf.poll_activity_task(name)
        grow(task)


@parsable.command
def init(theory):
    '''
    Initialize atlas for growing.
    '''
    with pomagma.util.chdir(pomagma.util.DATA):
        atlas = '{}/atlas.h5'.format(theory)
        size = pomagma.util.MIN_SIZES[theory]
        log_file = '{}/init.log'
        pomagma.actions.init(theory, atlas, size, log_file=log_file)
        pomagma.store.put(atlas)


@parsable.command
def clean(theory):
    '''
    Clean out all structures for theory.
    '''
    print 'Are you sure? [y/N]'
    if raw_input()[:1].lower() != 'y':
        return
    filenames = pomagma.store.listdir(theory)
    for filename in filenames:
        print 'removing', filename
        pomagma.store.s3_remove(filename)
    with pomagma.util.chdir(pomagma.util.DATA):
        shutil.rmtree(theory)


if __name__ == '__main__':
    parsable.dispatch()
