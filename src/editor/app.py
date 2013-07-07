import os
import bottle
import pomagma.corpus


PORT = int(os.environ.get('POMAGMA_EDITOR_PORT', 8080))
STATIC = os.path.join(pomagma.util.SRC, 'editor', 'static')


@bottle.route('/')
def serve_index():
    return bottle.static_file('index.html', root=STATIC)


@bottle.route('/static/<filepath:path>')
def serve_static(filepath):
    return bottle.static_file(filepath, root=STATIC)


if __name__ == '__main__':
    bottle.run(host='localhost', port=PORT, debug=True)
