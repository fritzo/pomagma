import simplejson as json
import parsable
import pomagma.workflow.util


def TODO(message):
    raise NotImplementedError('TODO {}'.format(message))


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

        TODO('get atlas if not cached locally')
        TODO('trim atlas to seed')
        TODO('put seed')

        result = {
            'nextActivity': {
                'activityType': '{}_{}_{}'.format('Grow', theory, size),
                'input': {
                    'seedFile': seed_file,
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

        TODO('get atlas if not cached locally')
        TODO('get seed if not cached locally')
        TODO('aggregate')
        TODO('put atlas')

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

        TODO('get seed')
        TODO('grow')
        TODO('put chart')

        result = {
            'nextActivity': {
                'activityType': '{}_{}'.format('Aggregate', theory),
                'input': {
                    'chartFile': chart_file,
                    },
                }
            }
        pomagma.workflow.util.finish_activity_task(task, result)


if __name__ == '__main__':
    parsable.dispatch()
