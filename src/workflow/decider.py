'''
Simple decider for linear workflows.
'''

import simplejson as json
import parsable
import pomagma.workflow.swf
import pomagma.workflow.reporter


def simple_decide(task, nextActivity):
    activity_type = nextActivity['activityType']
    json_input = nextActivity['input']
    input = json.dumps(json_input)
    pomagma.workflow.swf.decide_to_schedule(task, activity_type, input)


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
def start():
    '''
    Start decider, typically on master node.
    '''
    name = 'Simple'
    pomagma.workflow.swf.register_domain()
    print 'Starting decider'
    while True:
        task = pomagma.workflow.swf.poll_decision_task(name)
        events = [
            e for e in iter_recent_events(task)
            if not e['eventType'].startswith('Decision')
        ]

        last_event = events[0]
        event_type = last_event['eventType']
        print 'Processing', event_type

        if event_type == 'WorkflowExecutionStarted':
            attrs = last_event['workflowExecutionStartedEventAttributes']
            nextActivity = json.loads(attrs['input'])
            simple_decide(task, nextActivity)

        elif event_type == 'ActivityTaskCompleted':
            attrs = last_event['activityTaskCompletedEventAttributes']
            result = json.loads(attrs.get('result') or '{}')
            nextActivity = result.get('nextActivity')
            if nextActivity:
                simple_decide(task, nextActivity)
            else:
                pomagma.workflow.swf.decide_to_complete(task)

        elif event_type == 'ActivityTaskFailed':
            print 'ERROR task failed'
            attrs = last_event['activityTaskFailedEventAttributes']
            print 'Reason:\n'.format(attrs.get('reason', 'unknown'))
            print 'Details:\n{}'.format(attrs.get('details', 'none'))
            # activity_type = 'Report'
            # subject = '{} {}'.format(DOMAIN, event_type)
            # message = 'Reason: {}\nDetail:\n{}'.format(
            #    attrs.get('reason', 'unknown'),
            #    attrs.get('detail', 'none'))
            # json_input = {'subject': subject, 'message': message}
            # input = json.dumps(json_input)
            # pomagma.workflow.swf.decide_to_schedule(
            #    task,
            #    activity_type,
            #    input,
            #    )

        elif event_type == 'ScheduleActivityTaskFailed':
            print 'ERROR failed to schedule task'
            attrs = last_event['scheduleActivityTaskFailedEventAttributes']
            print 'Cause:', attrs.get('cause', 'unknown')

        elif event_type == 'ActivityTaskTimedOut':
            print 'ERROR canceling workflow after timeout'
            pomagma.workflow.swf.decide_to_complete(task)


if __name__ == '__main__':
    parsable.dispatch()
