'''
Simple decider for linear workflows.
'''

import simplejson as json
import parsable
import pomagma.workflow.swf
import pomagma.workflow.reporter


def simple_decide(nextActivity):
    activity_type = nextActivity['activityType']
    json_input = nextActivity['input']
    input = json.dumps(json_input)
    pomagma.workflow.swf.decide_to_schedule(activity_type, input)


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
    while True:
        task = pomagma.workflow.swf.poll_decision_task(name)
        events = [
            e for e in iter_recent_events(task)
            if not e['eventType'].startswith('Decision')
            ]

        last_event = events[0]
        event_type = last_event['eventType']

        if event_type == 'WorkflowExecutionStarted':
            nextActivity = json.loads(last_event['input'])
            simple_decide(nextActivity)

        elif event_type == 'ActivityTaskCompleted':
            result = json.loads(last_event.get('result', ''))
            nextActivity = result.get('nextActivity')
            if nextActivity:
                simple_decide(nextActivity)
            else:
                pomagma.workflow.swf.decide_to_complete(task)

        elif event_type == 'ActivityTaskFailed':
            activity_type = 'Report'
            subject = last_event.get('reason', 'Unknown failure')
            message = last_event.get('detail', '(no details available)')
            json_input = {'subject': subject, 'message': message}
            input = json.dumps(json_input)
            pomagma.workflow.swf.decide_to_schedule(activity_type, input)

        elif event_type == 'ActivityTaskTimedOut':
            print 'ERROR canceling workflow after timeout'
            pomagma.workflow.swf.decide_to_complete(task)


if __name__ == '__main__':
    parsable.dispatch()
