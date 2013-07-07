import os
import datetime
import bottle
import beaker.middleware
import cork
import parsable
parsable = parsable.Parsable()
import pomagma.util
import pomagma.corpus


PORT = int(os.environ.get('POMAGMA_EDITOR_PORT', 8080))
STATIC = os.path.join(pomagma.util.SRC, 'editor', 'static')
AUTH = os.path.join(pomagma.util.DATA, 'users')


if not os.path.exists(AUTH):
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


auth = cork.Cork(AUTH)

# wtf http://stackoverflow.com/questions/14818550
#app = bottle.default_app()
app = bottle.app()

session_options = {
    'session.type': 'cookie',
    'session.validate_key': True,
    'session.cookie_expires': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.encrypt_key': pomagma.util.random_uuid(),
}
app = beaker.middleware.SessionMiddleware(app, session_options)


def post_get(name, default=''):
    return bottle.request.POST.get(name, default).strip()


@bottle.route('/login', method='POST')
def login():
    username = post_get('username')
    password = post_get('password')
    auth.login(
        username,
        password,
        success_redirect='/',
        fail_redirect='/login')


@bottle.route('/login')
def login_form():
    return '''
        <form method="POST" action="/login">
        Username <input name="username" type="text" /> <br />
        Password <input name="password" type="password" /> <br />
        <input type="submit" />
        </form>
        '''

@bottle.route('/logout')
def logout():
    auth.current_user.logout(redirect='/login')


@bottle.route('/')
def index():
    auth.require(fail_redirect='/login')
    return bottle.static_file('index.html', root=STATIC)


@bottle.route('/static/<filepath:path>')
def static(filepath):
    auth.require(fail_redirect='/login')
    return bottle.static_file(filepath, root=STATIC)


@parsable.command
def serve(port=PORT):
    '''
    Start editor server.
    '''
    bottle.run(app=app, host='localhost', port=port, debug=True)


if __name__ == '__main__':
    parsable.dispatch()
