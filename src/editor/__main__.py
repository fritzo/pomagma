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


@bottle.route('/info')
def _info():
    return {
        'remote_addr': bottle.request.remote_addr,
        'remote_route': bottle.request.remote_route,
    }


@bottle.route('/login')
def login_form():
    return '''
        <form method="POST" action="/login">
        Username <input name="username" type="text" /> <br />
        Password <input name="password" type="password" /> <br />
        <input type="submit" />
        </form>
        '''


@bottle.route('/login', method='POST')
def login():
    username = bottle.request.POST.get('username', '').strip()
    password = bottle.request.POST.get('password', '').strip()
    pomagma.editor.auth.login(
        username,
        password,
        success_redirect='/',
        fail_redirect='/login')


@bottle.route('/logout')
def logout():
    pomagma.editor.auth.current_user.logout(redirect='/login')


@bottle.route('/test')
def _test():
    pomagma.editor.auth.require(fail_redirect='/login')
    return bottle.static_file('test.html', root=STATIC)


@bottle.route('/')
def get_index():
    pomagma.editor.auth.require(fail_redirect='/login')
    return bottle.static_file('index.html', root=STATIC)


@bottle.route('/static/<filepath:path>')
def get_static(filepath):
    pomagma.editor.auth.require(fail_redirect='/login')
    return bottle.static_file(filepath, root=STATIC)


@bottle.route('/corpus', method='GET')
def get_corpus():
    pomagma.editor.auth.require(fail_redirect='/login')
    modules = pomagma.corpus.list_modules()
    return {'modules': modules}


@bottle.route('/corpus/<module_name>', method='GET')
def get_module(module_name):
    pomagma.editor.auth.require(fail_redirect='/login')
    module = pomagma.corpus.load_module(module_name)
    return {'module': module}


@bottle.route('/corpus/<module_name>', method='PUT')
def put_module(module_name):
    pomagma.editor.auth.require(fail_redirect='/login')
    module = bottle.request.json
    assert module is not None, 'failed to store module {}'.format(module_name)
    pomagma.corpus.store_module(module_name, module)


@parsable.command
def serve(port=PORT):
    '''
    Start editor server.
    '''
    bottle.run(app=app, host='localhost', port=port, debug=True, reloader=True)


if __name__ == '__main__':
    parsable.dispatch()
