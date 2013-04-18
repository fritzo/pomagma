'''
Wrapper for Amazon SWF (Simple Workflows).

References:
http://docs.aws.amazon.com/amazonswf/latest/developerguide
http://docs.aws.amazon.com/amazonswf/latest/apireference
http://boto.readthedocs.org/en/2.6.0/ref/swf.html
https://github.com/boto/boto/blob/develop/boto/swf/layer1.py
https://github.com/boto/boto/blob/develop/boto/swf/layer1_decisions.py
https://github.com/boto/boto/blob/develop/boto/swf/exceptions.py
'''

import os
import functools
import simplejson as json
import traceback
import boto.swf
import boto.swf.layer1
import boto.swf.layer1_decisions
import boto.swf.exceptions
import pomagma.util
import pomagma.store


def try_connect_swf():
    try:
        return boto.swf.layer1.Layer1()
    except boto.exception.NoAuthHandlerFound:
        print 'WARNING failed to connect to SWF'


DOMAIN = os.environ.get('POMAGMA_DOMAIN', 'pomagma')
VERSION = '1.0.13'
SWF = try_connect_swf()

HEARTBEAT_TIMEOUT = 1200
SCHEDULE_TO_CLOSE_TIMEOUT = 1200
SCHEDULE_TO_START_TIMEOUT = 300
START_TO_CLOSE_TIMEOUT = 900
EXECUTION_TIMEOUT = 2400
TASK_TIMEOUT = 1200


#-----------------------------------------------------------------------------
# Admin


def register_domain():
    print 'Registering', DOMAIN
    try:
        SWF.register_domain(
            name=DOMAIN,
            workflow_execution_retention_period_in_days='90')
        print 'Registered', DOMAIN
    except boto.swf.exceptions.SWFDomainAlreadyExistsError:
        print DOMAIN, 'is already registered'
        pass


def register_activity_type(
        name,
        heartbeat_timeout=HEARTBEAT_TIMEOUT,
        schedule_to_close_timeout=SCHEDULE_TO_CLOSE_TIMEOUT,
        schedule_to_start_timeout=SCHEDULE_TO_START_TIMEOUT,
        start_to_close_timeout=START_TO_CLOSE_TIMEOUT,
        ):
    activity_type = '{}ActivityType'.format(name)
    task_list = '{}TaskList'.format(name)
    print 'Registering', activity_type
    try:
        SWF.register_activity_type(
            DOMAIN,
            activity_type,
            VERSION,
            task_list,
            str(heartbeat_timeout),
            str(schedule_to_close_timeout),
            str(schedule_to_start_timeout),
            str(start_to_close_timeout),
            )
        print 'Registered', activity_type
    except boto.swf.exceptions.SWFTypeAlreadyExistsError:
        print activity_type, 'is already registered'
        pass


def register_workflow_type(
        workflow,
        task_list,
        child_policy='TERMINATE',
        execution_timeout=EXECUTION_TIMEOUT,
        task_timeout=TASK_TIMEOUT,
        ):
    workflow = '{}WorkflowType'.format(workflow)
    task_list = '{}TaskList'.format(task_list)
    print 'Registering', workflow
    try:
        SWF.register_workflow_type(
            DOMAIN,
            workflow,
            VERSION,
            task_list,
            child_policy,
            str(execution_timeout),
            str(task_timeout),
            )
        print 'Registered', workflow
    except boto.swf.exceptions.SWFTypeAlreadyExistsError:
        print workflow, 'is already registered'
        pass


def start_workflow_execution(workflow_id, name, input=None):
    workflow_type = '{}WorkflowType'.format(name)
    print 'Starting', workflow_type, workflow_id
    SWF.start_workflow_execution(
        domain=DOMAIN,
        workflow_id=workflow_id,
        workflow_name=workflow_type,
        workflow_version=VERSION,
        input=input,
        )


#-----------------------------------------------------------------------------
# Decisions

def poll_decision_task(name):
    task_list = '{}TaskList'.format(name)
    while True:
        print 'Polling', task_list
        response = SWF.poll_for_decision_task(DOMAIN, task_list)
        if response.get('taskToken'):
            print 'Decision Task: {}'.format(response)
            return response


def decide_to_schedule(decision_task, activity_type, input=None):
    activity_type = '{}ActivityType'.format(activity_type)
    task_token = decision_task['taskToken']
    decisions = boto.swf.layer1_decisions.Layer1Decisions()
    activity_id = pomagma.util.random_uuid()
    print 'Scheduling', activity_type
    decisions.schedule_activity_task(
        activity_id=activity_id,
        activity_type_name=activity_type,
        activity_type_version=VERSION,
        input=input,
        )
    SWF.respond_decision_task_completed(task_token, decisions._data)


def decide_to_complete(decision_task):
    task_token = decision_task['taskToken']
    decisions = boto.swf.layer1_decisions.Layer1Decisions()
    decisions.complete_workflow_execution()
    SWF.respond_decision_task_completed(task_token, decisions._data)


def decide_to_fail(decision_task):
    task_token = decision_task['taskToken']
    decisions = boto.swf.layer1_decisions.Layer1Decisions()
    decisions.fail_workflow_execution()
    SWF.respond_decision_task_completed(task_token, decisions._data)


#-----------------------------------------------------------------------------
# Activities

def poll_activity_task(name):
    task_list = '{}TaskList'.format(name)
    while True:
        print 'Polling', task_list
        response = SWF.poll_for_activity_task(DOMAIN, task_list)
        if response.get('taskToken'):
            print 'Activity Task: {}'.format(response)
            return response


def finish_activity_task(task, result=None):
    SWF.respond_activity_task_completed(task['taskToken'], result=result)


def fail_activity_task(task, reason=None, details=None):
    SWF.respond_activity_task_failed(
        task['taskToken'],
        reason=reason,
        details=details)


def reproducible(module):
    '''
    Create decorator to run activities inreproducible environment.

    TODO send log file in error message
    '''
    module = 'pomagma.workflow.{}'.format(module)
    def reproducible_(fun):
        @functools.wraps(fun)
        def reproducible_fun(task):
            try:
                with pomagma.util.chdir(pomagma.util.DATA):
                    result = fun(task)
                if result is not None:
                    result = json.dumps(result)
                finish_activity_task(task, result)
            except Exception, exc:
                print 'ERROR {}.{} failed'.format(module, fun.__name__)
                trace = traceback.format_exc()
                reason = str(exc)
                #task_str = json.dumps(task, sort_keys=True)
                details = '\n'.join([
                    trace,
                    # FIXME need environment variables and all manner of muck
                    #'To Reproduce:',
                    #'import simplejson as json',
                    #'import pomagma.util',
                    #'import {}'.format(module),
                    #'task = json.load({})'.format(repr(task_str)),
                    #'with pomagma.util.chdir(pomagma.util.DATA):',
                    #'    {}.{}({})'.format(module, fun.__name__, task),
                    ])
                print details
                fail_activity_task(task, reason, details)
        return reproducible_fun
    return reproducible_
