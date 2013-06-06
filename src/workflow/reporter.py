# adapted from http://docs.python.org/2/library/email-examples.html

import os
import simplejson as json
import smtplib
from email.mime.text import MIMEText
import parsable
import pomagma.workflow.swf


SENDER = 'automated@pomagma.info'
RECIPIENT = os.environ.get('POMAGMA_EMAIL')


def email(args):
    subject = args['subject']
    message = args['message']
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = SENDER
    msg['To'] = RECIPIENT

    s = smtplib.SMTP('localhost')
    s.sendmail(SENDER, [RECIPIENT], msg.as_string())
    s.quit()


@parsable.command
def start():
    '''
    Start reporter, typically on master node.
    '''
    name = 'Report'
    pomagma.workflow.swf.register_activity_type(name)
    print 'Starting reporter'
    while True:
        task = pomagma.workflow.swf.poll_activity_task(name)
        input = json.loads(task['input'])
        email(input)
        pomagma.workflow.swf.finish_activity_task(task)


if __name__ == '__main__':
    parsable.dispatch()
