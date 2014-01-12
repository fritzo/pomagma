import os
from itertools import izip
import bottle
import pomagma.util
import pomagma.corpus
import pomagma.analyst
import mimetypes


PORT = int(os.environ.get('POMAGMA_EDITOR_PORT', 34934))
STATIC = os.path.join(pomagma.util.SRC, 'editor', 'static')
CORPUS = pomagma.corpus.Corpus()
ANALYST = pomagma.analyst.connect()


def get_lines():
    lines = [
        {'id': str(id), 'name': name, 'code': code}
        for id, name, code in CORPUS.find_all()
    ]
    return lines


def get_validitated_lines():
    lines = get_lines()
    validities = ANALYST.validate_corpus(lines)
    for line, validity in izip(lines, validities):
        line['validity'] = validity
    return lines


mimetypes.add_type('application/font-woff', '.woff')


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


@bottle.route('/corpus/lines', method='GET')
def get_corpus():
    require_auth()
    lines = get_lines()
    return {'data': lines}


@bottle.route('/corpus/line/<line_id>', method='GET')
def get_line(line_id):
    require_auth()
    id = int(line_id)
    line = CORPUS.find_by_id(id)
    return {'data': line}


@bottle.route('/corpus/line', method='POST')
def post_line():
    require_auth()
    line = bottle.request.json
    name = line['name']
    code = line['code']
    id = CORPUS.insert(name, code)
    return {'data': id}


@bottle.route('/corpus/line/<line_id>', method='PUT')
def put_line(line_id):
    require_auth()
    line = bottle.request.json
    name = line['name']
    code = line['code']
    id = int(line_id)
    CORPUS.update(id, name, code)


@bottle.route('/corpus/line/<line_id>', method='DELETE')
def delete_line(line_id):
    require_auth()
    id = int(line_id)
    CORPUS.remove(id)


@bottle.route('/corpus/validities', method='GET')
def get_validities():
    require_auth()
    lines = get_lines()
    validities = ANALYST.validate_corpus(lines)
    for line, validity in izip(lines, validities):
        validity['id'] = line['id']
    return {'data': validities}


def serve(port=PORT, reloader=True):
    '''
    Start editor server.
    '''
    bottle.run(host='localhost', port=port, debug=True, reloader=reloader)
