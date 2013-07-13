import os
import bottle
import pomagma.util
import pomagma.corpus


PORT = int(os.environ.get('POMAGMA_EDITOR_PORT', 34934))
STATIC = os.path.join(pomagma.util.SRC, 'editor', 'static')
CORPUS = pomagma.corpus.Corpus()


@bottle.route('/info')
def _info():
    return {
        'remote_addr': bottle.request.remote_addr,
        'remote_route': bottle.request.remote_route,
    }


def require_auth():
    if bottle.request.remote_route != ['127.0.0.1']:
        raise bottle.HTTPError(403)


@bottle.route('/test')
def _test():
    require_auth()
    return bottle.static_file('test.html', root=STATIC)


@bottle.route('/')
def get_index():
    require_auth()
    return bottle.static_file('index.html', root=STATIC)


@bottle.route('/static/<filepath:path>')
def get_static(filepath):
    require_auth()
    return bottle.static_file(filepath, root=STATIC)


# TODO revise corpus methods
@bottle.route('/corpus', method='GET')
def get_corpus():
    require_auth()
    modules = pomagma.corpus.list_modules()
    return {'modules': modules}


@bottle.route('/corpus/<module_name>', method='GET')
def get_module(module_name):
    require_auth()
    module = pomagma.corpus.load_module(module_name)
    return {'module': module}


@bottle.route('/corpus/<module_name>', method='PUT')
def put_module(module_name):
    require_auth()
    module = bottle.request.json
    assert module is not None, 'failed to store module {}'.format(module_name)
    pomagma.corpus.store_module(module_name, module)


def serve(port=PORT):
    '''
    Start editor server.
    '''
    bottle.run(host='localhost', port=port, debug=True, reloader=True)
