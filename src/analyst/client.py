import zmq
import pomagma.util
from pomagma.analyst import messages_pb2 as messages

CONTEXT = zmq.Context()


class Client(object):
    def __init__(self, port):
        self.socket = CONTEXT.socket(zmq.REQ)
        self.socket.connect('tcp://localhost:{}'.format(port))

    def simplify(self, codes):
        request = messages.AnalystRequest()
        request.request_id = pomagma.util.random_uuid()
        simplify_request = request.simplify_request.add()
        for code in codes:
            simplify_request.add(code)
        self.socket.send(request.toByteArray(), 0)
        raise NotImplementedError('TODO get response')

    def validate(self, lines):
        raise NotImplementedError('TODO')
