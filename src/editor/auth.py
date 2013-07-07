import os
import datetime
import cork
import parsable
parsable = parsable.Parsable()
import pomagma.util


AUTH = os.path.join(pomagma.util.DATA, 'users')


@parsable.command
def init():
    '''
    Initialize cork authorization database.
    '''
    assert not os.path.exists(AUTH), 'auth already initialized'
    print 'Initializing cork auth'
    os.makedirs(AUTH)
    auth = cork.Cork(AUTH, initialize=True)

    auth._store.roles['admin'] = 100
    auth._store.roles['editor'] = 60
    auth._store.roles['user'] = 50
    auth._store.save_roles()

    username = password = 'admin'
    timestamp = str(datetime.datetime.utcnow())
    username = password = 'admin'
    auth._store.users[username] = {
        'role': 'admin',
        'hash': auth._hash(username, password),
        'email_addr': username + '@localhost.local',
        'desc': username + ' test user',
        'creation_date': timestamp,
    }
    username = password = ''
    auth._store.users[username] = {
        'role': 'user',
        'hash': auth._hash(username, password),
        'email_addr': username + '@localhost.local',
        'desc': username + ' test user',
        'creation_date': timestamp,
    }
    auth._store.save_users()


class Stub():
    def __call__(self, *args, **kwargs):
        pass

    def __getattr__(self, *args, **kwargs):
        pass


def require_stub():
    assert bottle.request.remote_addr == '127.0.0.1', 'auth failed'
    assert bottle.request.remote_route == ['127.0.0.1'], 'auth failed'


active = os.path.exists(AUTH)

if active:
    auth = cork.Cork(AUTH)
    require = auth.require
    login = auth.login
else:
    print 'WARNING cork auth disabled'
    require = Stub()
    login = Stub()

if __name__ == '__main__':
    parsable.dispatch()
