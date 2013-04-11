# adapted from http://docs.python.org/2/library/email-examples.html

import os
import simplejson as json
import smtplib
from email.mime.text import MIMEText
import parsable
import pomagma.workflow.swf


SPAMMER = 'automated@pomagma.info'
SPAMMEE = os.environ.get('POMAGMA_SPAMMEE')


def email(args):
    subject = args['subject']
    message = args['message']
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = SPAMMER
    msg['To'] = SPAMMEE

    s = smtplib.SMTP('localhost')
    s.sendmail(SPAMMER, [SPAMMEE], msg.as_string())
    s.quit()


@parsable.command
def start():
    '''
    Start reporter, typically on master node.
    '''
    name = 'Report'
    pomagma.workflow.swf.register_activity_type(name)
    while True:
        task = pomagma.workflow.swf.poll_activity_task(name)
        input = json.loads(task['input'])
        email(input)
        pomagma.workflow.swf.finish_activity_task(task)


if __name__ == '__main__':
    parsable.dispatch()
