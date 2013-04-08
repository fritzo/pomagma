import simplejson as json
import parsable
import pomagma.util
import pomagma.store
import pomagma.wrapper
import pomagma.workflow.util


STEP_SIZE = 512


def random_filename():
    return 'temp/{}.h5'.format(pomagma.workflow.util.random_uuid())


def normalize_filename(prefix, old_filename):
    hash_ = pomagma.util.get_hash(old_filename)
    new_filename = '{}/{}.h5'.format(prefix, hash_)
    os.rename(old_filename, new_filename)
    return new_filename


def init_atlas(theory):
    filenames = pomagma.store.listdir('{}/atlas/'.format(theory))
    if filenames:
        raise ValueError('Atlas already exists')
    return '{}/atlas/0.h5'.format(theory)


def get_atlas(theory):
    filenames = pomagma.store.listdir('{}/atlas/'.format(theory))
    versions = [int(filename.lstrip('.h5.bz2')) for f in filenames]
    if not versions:
        raise ValueError('Atlas has not been initialized')
    version = max(versions)
    filename = '{}/atlas/{}.h5'.format(theory, version)
    return version, pomagma.store.get(filename)


def put_atlas(theory, version):
    filenames = pomagma.store.listdir('{}/atlas/'.format(theory))
    versions = [int(filename.lstrip('.h5.bz2')) for f in filenames]
    if version in versions:
        raise ValueError('Atlas version {} already exists'.format(version))
    filename = '{}/atlas/{}.h5'.format(theory, version)
    pomagma.store.put(filename)


def iter_recent_events(decision_task):
    '''
    Reverse-chronologically iterats over events since the last decision.
    '''
    prev_id = decision_task['previousStartedEventId']
    events = decision_task['events']
    for event in reversed(events):
        if event['eventType'] == 'DecisionTaskStarted':
            if event['eventId'] == prev_id:
                break
        yield event


# see http://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-using-swf-api.html#swf-dg-error-handling
FAILURE_MODES = set([
    'ActivityTaskFailed',
    'ActivityTaskTimedOut',
    ])


@parsable.command
def start_decider():
    '''
    Start grow decider, typically on master node.
    '''
    name = 'Grow'
    pomagma.workflow.util.register_domain()
    pomagma.workflow.util.register_workflow_type(name)
    while True:
        task = pomagma.workflow.util.poll_decision_task(name)
        events = [
            e for e in iter_recent_events(task)
            if not e['eventType'].startswith('Decision')
            ]

        last_event = events[0]
        event_type = last_event['eventType']

        if event_type == 'WorkflowExecutionStarted':
            activity_type = 'Trim'
            input = last_event['input']
            pomagma.workflow.util.decide_to_schedule(activity_type, input)

        elif event_type == 'ActivityTaskCompleted':
            result = json.loads(last_event.get('result', ''))
            nextActivity = result.get('nextActivity')
            if nextActivity:
                activity_type = nextActivity['activityType']
                json_input = nextActivity['input']
                input = json.dumps(json_input)
                pomagma.workflow.util.decide_to_schedule(activity_type, input)
            else:
                pomagma.workflow.util.decide_to_complete(task)

        elif event_type in FAILURE_MODES:
            print 'ERROR canceling workflow after {}'.format(event_type)
            pomagma.workflow.util.decide_to_complete(task)


@parsable.command
def start_trimmer():
    '''
    Start trimmer, typically on a high-memory node.
    '''
    name = 'Trim'
    pomagma.workflow.util.register_activity_type(name)
    while True:
        task = pomagma.workflow.util.poll_activity_task(name)
        input = json.loads(task['input'])
        theory = input['theory']
        size = input['size']
        min_size = pomagma.util.MIN_SIZES[theory]
        seed_size = max(min_size, size - STEP_SIZE)

        with pomagma.util.chdir(pomagma.util.DATA):
            atlas = pomagma.store.get('/{}/atlas.h5'.format(theory))
            atlas_size = pomagma.util.get_info(atlas)['item_count']
            if seed_size < atlas_size:
                seed = random_filename()
                pomagma.wrapper.trim(theory, atlas, seed, size)
            else:
                seed = atlas
            seed = normalize_filename('{}/seed'.format(theory), seed)
            pomagma.store.put(seed)

        result = {
            'nextActivity': {
                'activityType': '{}_{}_{}'.format('Grow', theory, size),
                'input': {
                    'seedFile': seed,
                    },
                }
            }
        pomagma.workflow.util.finish_activity_task(task, result)


@parsable.command
def start_aggregator(theory):
    '''
    Start aggregator, typically on a high-memory node.
    WARNING There may be exactly one aggregator per theory.
    '''
    name = '{}_{}'.format('Aggregate', theory)
    pomagma.workflow.util.register_activity_type(name)
    while True:
        task = pomagma.workflow.util.poll_activity_task(name)
        input = json.loads(task['input'])
        chart = input['chartFile']

        with pomagma.util.chdir(pomagma.util.DATA):
            atlas = pomagma.store.get('/{}/atlas.h5'.format(theory))
            chart = pomagma.store.get(chart)
            pomagma.wrapper.aggregate(atlas, chart, atlas)
            pomagma.store.put(atlas)
            pomagma.store.remove_local(chart)

        pomagma.workflow.util.finish_activity_task(task)


@parsable.command
def start_grower(theory, size):
    '''
    Start grow worker, typically on a high-memory high-cpu node.
    '''
    workflow_name = 'Grow'
    name = '{}_{}_{}'.format('Grow', theory, size)
    param = json.dumps({'theory': theory, 'size': size})
    pomagma.workflow.util.register_activity_type(name)
    while True:
        pomagma.workflow.util.start_workflow_execution(workflow_name, param)
        task = pomagma.workflow.util.poll_activity_task(name)
        input = json.loads(task['input'])
        seed = input['seedFile']

        with pomagma.util.chdir(pomagma.util.DATA):
            seed = pomagma.store.get(seed)
            seed_size = pomagma.util.get_info(atlas)['item_count']
            chart_size = min(size, seed_size + STEP_SIZE)
            chart = random_filename()
            pomagma.wrapper.grow(theory, seed, chart, chart_size)
            chart = normalize_filename('{}/chart'.format(theory), chart)
            pomagma.store.put(chart)
            pomagma.store.remove_local(seed)

        result = {
            'nextActivity': {
                'activityType': '{}_{}'.format('Aggregate', theory),
                'input': {
                    'chartFile': chart,
                    },
                }
            }
        pomagma.workflow.util.finish_activity_task(task, result)


@parsable.command
def init(theory):
    '''
    Initialize atlas for growing.
    '''
    with pomagma.util.chdir(pomagma.util.DATA):
        atlas = init_atlas()
        size = pomagma.util.MIN_SIZES[theory]
        pomagma.wrapper.init(theory, atlas, size)
        pomagma.store.put(atlas)


@parsable.command
def clean(theory):
    '''
    Clean out all structures for theory.
    '''
    print 'Are you sure? [y/N]'
    if raw_input()[:1].lower() != 'y':
        return
    filenames = pomagma.store.listdir('{}'.format(theory))
    for filename in filenames:
        pomagma.store.s3_remove(filename)
    with pomagma.util.chdir(pomagma.util.DATA):
        shutil.rmtree(theory)


if __name__ == '__main__':
    parsable.dispatch()
