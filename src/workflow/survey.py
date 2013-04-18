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
def init(theory):
    '''
    Initialize atlas for surveying.
    Requires: medium-memory, high-cpu.
    '''
    with pomagma.util.chdir(pomagma.util.DATA):
        atlas = '{}/atlas.h5'.format(theory)
        size = pomagma.util.MIN_SIZES[theory]
        log_file = '{}/init.log'
        pomagma.actions.init(theory, atlas, size, log_file=log_file)
        pomagma.store.put(atlas)


def trim(theory, size):
    min_size = pomagma.util.MIN_SIZES[theory]
    seed_size = max(min_size, size - STEP_SIZE)
    atlas = pomagma.store.get('{}/atlas.h5'.format(theory))
    atlas_size = get_size(atlas)
    if seed_size < atlas_size:
        seed = random_filename()
        log_file = '{}/advise.log'.format(theory)
        pomagma.actions.trim(theory, atlas, seed, size, log_file=log_file)
    else:
        seed = atlas
    seed = normalize_filename('{}/seed'.format(theory), seed)
    pomagma.store.put(seed)
    return seed


def aggregate(theory, chart):
    atlas = pomagma.store.get('{}/atlas.h5'.format(theory))
    chart = pomagma.store.get(chart)
    log_file = '{}/advisor.log'.format(theory)
    pomagma.actions.aggregate(atlas, chart, atlas, log_file=log_file)
    pomagma.store.put(atlas)
    pomagma.store.remove(chart)


@reproducible
def advise(task):
    args = json.loads(task['input'])
    action = args['advisorAction']
    if action == 'Trim':
        theory = args['theory']
        size = args['size']
        seed = trim(theory, size)
        return {
            'nextActivity': {
                'activityType': '{}_{}_{}'.format('Survey', theory, size),
                'input': {
                    'theory': theory,
                    'size': size,
                    'seedFile': seed,
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
    seed = args['seedFile']
    seed = pomagma.store.get(seed)
    seed_size = get_size(seed)
    chart_size = min(size, seed_size + STEP_SIZE)
    chart = random_filename()
    log_file = '{}/survey.log'.format(theory)
    pomagma.actions.survey(theory, seed, chart, chart_size, log_file=log_file)
    chart = normalize_filename('{}/chart'.format(theory), chart)
    pomagma.store.put(chart)
    pomagma.store.remove(seed)
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
