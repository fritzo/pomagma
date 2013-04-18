'''
Activities for survey workflow.

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

reproducible = pomagma.workflow.swf.reproducible(__name__)


def random_filename():
    return 'temp/{}.h5'.format(pomagma.util.random_uuid())


def normalize_filename(prefix, old_filename):
    hash_ = pomagma.util.get_hash(old_filename)
    new_filename = '{}/{}.h5'.format(prefix, hash_)
    os.rename(old_filename, new_filename)
    return new_filename


def get_size(filename):
    return pomagma.util.get_info(filename)['item_count']


@parsable.command
def init(laws):
    '''
    Initialize world map for surveying.
    Requires: medium-memory, high-cpu.
    '''
    with pomagma.util.chdir(pomagma.util.DATA):
        world = '{}/world.h5'.format(laws)
        size = pomagma.util.MIN_SIZES[laws]
        log_file = '{}/init.log'
        pomagma.actions.init(laws, world, size, log_file=log_file)
        pomagma.store.put(world)


def trim(laws, size):
    min_size = pomagma.util.MIN_SIZES[laws]
    region_size = max(min_size, size - STEP_SIZE)
    world = pomagma.store.get('{}/world.h5'.format(laws))
    world_size = get_size(world)
    if region_size < world_size:
        region = random_filename()
        log_file = '{}/advise.log'.format(laws)
        pomagma.actions.trim(laws, world, region, size, log_file=log_file)
    else:
        region = world
    region = normalize_filename('{}/region'.format(laws), region)
    pomagma.store.put(region)
    return region


def aggregate(laws, chart):
    world = pomagma.store.get('{}/world.h5'.format(laws))
    chart = pomagma.store.get(chart)
    log_file = '{}/advisor.log'.format(laws)
    pomagma.actions.aggregate(world, chart, world, log_file=log_file)
    pomagma.store.put(world)
    pomagma.store.remove(chart)


@reproducible
def advise(task):
    args = json.loads(task['input'])
    action = args['advisorAction']
    if action == 'Trim':
        laws = args['laws']
        size = args['size']
        region = trim(laws, size)
        return {
            'nextActivity': {
                'activityType': '{}_{}_{}'.format('Survey', laws, size),
                'input': {
                    'laws': laws,
                    'size': size,
                    'regionFile': region,
                    },
                }
            }
    else:
        assert action == 'Aggregate'
        laws = args['laws']
        chart = args['chartFile']
        aggregate(laws, chart)
        return None


@reproducible
def survey(task):
    args = json.loads(task['input'])
    laws = args['laws']
    size = args['size']
    region = args['regionFile']
    region = pomagma.store.get(region)
    region_size = get_size(region)
    chart_size = min(size, region_size + STEP_SIZE)
    chart = random_filename()
    log_file = '{}/survey.log'.format(laws)
    pomagma.actions.survey(laws, region, chart, chart_size, log_file=log_file)
    chart = normalize_filename('{}/chart'.format(laws), chart)
    pomagma.store.put(chart)
    pomagma.store.remove(region)
    return {
        'nextActivity': {
            'activityType': '{}_{}'.format('Advise', laws),
            'input': {
                'advisorAction': 'Aggregate',
                'laws': laws,
                'chartFile': chart,
                },
            }
        }


@parsable.command
def start_advisor(laws):
    '''
    Start advisor = aggregator + trimmer.
    Constraint: there must be exactly one advisor per laws.
    Requires: high-memory.
    '''
    activity_name = '{}_{}'.format('Advise', laws)
    pomagma.workflow.swf.register_activity_type(activity_name)
    while True:
        task = pomagma.workflow.swf.poll_activity_task(activity_name)
        advise(task)


@parsable.command
def start_surveyor(laws, size):
    '''
    Start survey worker.
    Requires: high-memory, high-cpu node.
    '''
    workflow_name = 'Survey'
    task_list = 'Simple'
    activity_name = '{}_{}_{}'.format('Survey', laws, size)
    nextActivity = {
        'activityType': '{}_{}'.format('Advise', laws),
        'input': {
            'advisorAction': 'Trim',
            'laws': laws,
            'size': size,
            }
        }
    input = json.dumps(nextActivity)
    pomagma.workflow.swf.register_activity_type(activity_name)
    pomagma.workflow.swf.register_workflow_type(workflow_name, task_list)
    while True:
        workflow_id = pomagma.util.random_uuid()
        pomagma.workflow.swf.start_workflow_execution(
                workflow_id,
                workflow_name,
                input)
        task = pomagma.workflow.swf.poll_activity_task(activity_name)
        survey(task)


@parsable.command
def clean(laws):
    '''
    Clean out all structures for laws.
    '''
    print 'Are you sure? [y/N]'
    if raw_input()[:1].lower() != 'y':
        return
    filenames = pomagma.store.listdir(laws)
    for filename in filenames:
        print 'removing', filename
        pomagma.store.s3_remove(filename)
    with pomagma.util.chdir(pomagma.util.DATA):
        shutil.rmtree(laws)


if __name__ == '__main__':
    parsable.dispatch()
