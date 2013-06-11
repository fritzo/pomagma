'''
Test workflow.
'''

import os
import simplejson as json
from nose.tools import assert_equal
import parsable
import pomagma.util
import pomagma.store
import pomagma.workflow.swf


ITERS = 5

reproducible = pomagma.workflow.swf.reproducible(__name__)


def random_filename():
    if not os.path.exists('test'):
        os.makedirs('test')
    return 'test/{}.text'.format(pomagma.util.random_uuid())


@reproducible
def step1(task):
    with pomagma.util.chdir(pomagma.util.DATA):
        args = json.loads(task['input'])
        state = args['state']
        filename = random_filename()
        with open(filename, 'w') as f:
            json.dump(state, f)
        pomagma.store.put(filename)
        return {
            'nextActivity': {
                'activityType': 'Step2',
                'input': {'filename': filename},
            }
        }


@reproducible
def step2(task):
    with pomagma.util.chdir(pomagma.util.DATA):
        args = json.loads(task['input'])
        filename = args['filename']
        pomagma.store.get(filename)
        with open(filename) as f:
            state = json.load(f)
        pomagma.store.remove(filename)
        return {
            'nextActivity': {
                'activityType': 'Step3',
                'input': {'state': state},
            }
        }


STATE = None


@reproducible
def step3(task):
    args = json.loads(task['input'])
    assert_equal(args['state'], STATE)


@parsable.command
def start(step):
    '''
    Start a processing step.
    '''
    assert pomagma.workflow.swf.DOMAIN == 'pomagma-test'
    assert pomagma.store.BUCKET.name == 'pomagma-test'
    step = int(step)
    assert step in [1, 2, 3], step
    activity_name = 'Step{}'.format(step)
    pomagma.workflow.swf.register_activity_type(activity_name)
    if step == 1:
        print 'Starting', activity_name
        for i in xrange(ITERS):
            task = pomagma.workflow.swf.poll_activity_task(activity_name)
            print 'iter', i, 'step1'
            step1(task)
    elif step == 2:
        print 'Starting', activity_name
        for i in xrange(ITERS):
            task = pomagma.workflow.swf.poll_activity_task(activity_name)
            print 'iter', i, 'step2'
            step2(task)
    else:
        workflow_name = 'Test'
        task_list = 'Simple'
        pomagma.workflow.swf.register_workflow_type(workflow_name, task_list)
        print 'Starting', activity_name
        for i in xrange(ITERS):
            print 'iter', i, 'step0'
            state = pomagma.util.random_uuid()
            workflow_id = '{}.{}'.format(state, i)
            nextActivity = {
                'activityType': 'Step1',
                'input': {'state': state},
            }
            input = json.dumps(nextActivity)
            pomagma.workflow.swf.start_workflow_execution(
                workflow_id,
                workflow_name,
                input)
            task = pomagma.workflow.swf.poll_activity_task(activity_name)
            print 'iter', i, 'step3'
            global STATE
            STATE = state
            step3(task)


if __name__ == '__main__':
    parsable.dispatch()
