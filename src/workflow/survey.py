'''
Activities for survey workflow.

References:
http://docs.aws.amazon.com/amazonswf/latest/developerguide/\
swf-dg-using-swf-api.html#swf-dg-error-handling
'''

import os
import shutil
import simplejson as json
import parsable
import pomagma.util
import pomagma.store
import pomagma.surveyor
import pomagma.cartographer
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
def init(theory):
    '''
    Initialize world map for surveying.
    Requires: medium-memory, high-cpu.
    '''
    with pomagma.util.chdir(pomagma.util.DATA):
        world = '{}/world.h5'.format(theory)
        size = pomagma.util.MIN_SIZES[theory]
        log_file = '{}/init.log'
        pomagma.surveyor.init(theory, world, size, log_file=log_file)
        pomagma.store.put(world)


def trim(theory, size):
    min_size = pomagma.util.MIN_SIZES[theory]
    region_size = max(min_size, size - STEP_SIZE)
    world = pomagma.store.get('{}/world.h5'.format(theory))
    world_size = get_size(world)
    if region_size < world_size:
        region = random_filename()
        log_file = '{}/advise.log'.format(theory)
        pomagma.cartographer.trim(
            theory,
            world,
            region,
            size,
            log_file=log_file)
    else:
        region = world
    region = normalize_filename('{}/region'.format(theory), region)
    pomagma.store.put(region)
    return region


def aggregate(theory, chart):
    world = pomagma.store.get('{}/world.h5'.format(theory))
    chart = pomagma.store.get(chart)
    log_file = '{}/advisor.log'.format(theory)
    pomagma.cartographer.aggregate(world, chart, world, log_file=log_file)
    pomagma.store.put(world)
    pomagma.store.remove(chart)


@reproducible
def advise(task):
    args = json.loads(task['input'])
    action = args['advisorAction']
    if action == 'Trim':
        theory = args['theory']
        size = args['size']
        region = trim(theory, size)
        return {
            'nextActivity': {
                'activityType': '{}_{}_{}'.format('Survey', theory, size),
                'input': {
                    'theory': theory,
                    'size': size,
                    'regionFile': region,
                    },
                }
            }
    else:
        assert action == 'Aggregate'
        theory = args['theory']
        chart = args['chartFile']
        aggregate(theory, chart)
        return None


@reproducible
def survey(task):
    args = json.loads(task['input'])
    theory = args['theory']
    size = args['size']
    region = args['regionFile']
    region = pomagma.store.get(region)
    region_size = get_size(region)
    chart_size = min(size, region_size + STEP_SIZE)
    chart = random_filename()
    log_file = '{}/survey.log'.format(theory)
    pomagma.surveyor.survey(
        theory,
        region,
        chart,
        chart_size,
        log_file=log_file)
    chart = normalize_filename('{}/chart'.format(theory), chart)
    pomagma.store.put(chart)
    pomagma.store.remove(region)
    return {
        'nextActivity': {
            'activityType': '{}_{}'.format('Advise', theory),
            'input': {
                'advisorAction': 'Aggregate',
                'theory': theory,
                'chartFile': chart,
                },
            }
        }


@parsable.command
def start_advisor(theory):
    '''
    Start advisor = aggregator + trimmer.
    Constraint: there must be exactly one advisor per theory.
    Requires: high-memory.
    '''
    activity_name = '{}_{}'.format('Advise', theory)
    pomagma.workflow.swf.register_activity_type(activity_name)
    with pomagma.util.chdir(pomagma.util.DATA):
        while True:
            task = pomagma.workflow.swf.poll_activity_task(activity_name)
            advise(task)


@parsable.command
def start_surveyor(theory, size):
    '''
    Start survey worker.
    Requires: high-memory, high-cpu node.
    '''
    workflow_name = 'Survey'
    task_list = 'Simple'
    activity_name = '{}_{}_{}'.format('Survey', theory, size)
    nextActivity = {
        'activityType': '{}_{}'.format('Advise', theory),
        'input': {
            'advisorAction': 'Trim',
            'theory': theory,
            'size': size,
            }
        }
    input = json.dumps(nextActivity)
    pomagma.workflow.swf.register_activity_type(activity_name)
    pomagma.workflow.swf.register_workflow_type(workflow_name, task_list)
    with pomagma.util.chdir(pomagma.util.DATA):
        while True:
            workflow_id = pomagma.util.random_uuid()
            pomagma.workflow.swf.start_workflow_execution(
                    workflow_id,
                    workflow_name,
                    input)
            task = pomagma.workflow.swf.poll_activity_task(activity_name)
            survey(task)


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
