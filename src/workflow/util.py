import uuid
import boto.swf
import boto.swf.layer1
import boto.swf.layer1_decisions
import boto.swf.exceptions


DOMAIN = 'pomagma'
VERSION = '1.0'
SWF = boto.swf.layer1.Layer1()


def random_uuid():
    return str(uuid.uuid4())


#-----------------------------------------------------------------------------
# Admin


def register_domain():
    print 'Registering domain'
    try:
        SWF.register_domain(
                name=DOMAIN,
                workflow_execution_retention_period_in_days=90)
    except boto.swf.exceptions.SWFDomainAlreadyExistsError:
        pass


def register_activity_type(name):
    activity_type = '{}ActivityType'.format(name)
    print 'Registering activity type {}'.format(activity_type)
    try:
        SWF.register_activity_type(DOMAIN, activity_type, VERSION)
    except boto.swf.exceptions.SWFTypeAlreadyExistsError:
        pass


def register_workflow_type(name):
    workflow_type = '{}ActivityType'.format(name)
    print 'Registering workflow type {}'.format(workflow_type)
    try:
        SWF.register_workflow_type(DOMAIN, workflow_type, VERSION)
    except boto.swf.exceptions.SWFTypeAlreadyExistsError:
        pass


def start_workflow_execution(workflow, version):
    SWF.start_workflow_execution(
        domain=DOMAIN,
        workflow_id=random_uuid(),
        workflow_name=workflow,
        version=VERSION)

#-----------------------------------------------------------------------------
# Decisions

def poll_decision_task(name):
    task_list = '{}TaskList'.format(name)
    while True:
        response = SWF.poll_for_decision_task(DOMAIN, task_list)
        if response['taskToken']:
            print 'Decision Task: {}'.format(response)
            return response


def decide_to_schedule(decision_task, activity_type, input=None):
    task_token = decision_task['taskToken']
    decisions = boto.swf.layer1_decisions.Layer1Decisions()
    task_list = '{}TaskList'.format(activity_type)
    activity_id = random_uuid()
    decisions.schedule_activity_task(
        activity_id=activity_id,
        activity_type_name='{}ActivityType'.format(activity_type),
        activity_type_version=VERSION,
        task_list=task_list,
        input=input,
        )
    SWF.respond_decision_task_completed(task_token, decisions)


def decide_to_complete(decision_task):
    task_token = decision_task['taskToken']
    decisions = boto.swf.layer1_decisions.Layer1Decisions()
    decisions.complete_workflow_execution()
    SWF.respond_decision_task_completed(task_token, decisions)

#-----------------------------------------------------------------------------
# Activities

def poll_activity_task(name):
    task_list = '{}TaskList'.format(name)
    while True:
        response = SWF.poll_for_activity_task(DOMAIN, task_list)
        if response['taskToken']:
            print 'Activity Task: {}'.format(response)
            return response


def finish_activity_task(task, result=None):
    SWF.respond_activity_task_completed(task['taskToken'], result=result)
