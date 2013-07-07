import os
import bottle
import beaker.middleware
import parsable
parsable = parsable.Parsable()
import pomagma.util
import pomagma.corpus
import pomagma.editor.auth


PORT = int(os.environ.get('POMAGMA_EDITOR_PORT', 34934))
STATIC = os.path.join(pomagma.util.SRC, 'editor', 'static')

app = bottle.app()

if pomagma.editor.auth.active:
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
    pomagma.editor.auth.login(
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
    pomagma.editor.auth.current_user.logout(redirect='/login')


@bottle.route('/')
def index():
    pomagma.editor.auth.require(fail_redirect='/login')
    return bottle.static_file('index.html', root=STATIC)


@bottle.route('/static/<filepath:path>')
def static(filepath):
    pomagma.editor.auth.require(fail_redirect='/login')
    return bottle.static_file(filepath, root=STATIC)


@parsable.command
def serve(port=PORT):
    '''
    Start editor server.
    '''
    bottle.run(app=app, host='localhost', port=port, debug=True, reloader=True)


if __name__ == '__main__':
    parsable.dispatch()
