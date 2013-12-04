import os
import sys
import zmq
import pomagma.util
from pomagma.analyst import messages_pb2 as messages


CONTEXT = zmq.Context()

Request = messages.AnalystRequest
Response = messages.AnalystResponse

TROOL = {
    Response.MAYBE: None,
    Response.TRUE: True,
    Response.FALSE: False,
}


def WARN(message):
    sys.stdout.write('WARNING {}\n'.format(message))
    sys.stdout.flush()


class ServerError(Exception):

    def __init__(self, messages):
        self.messages = list(messages)

    def __str__(self):
        return '\n'.join('Server Errors:' + self.messages)


class Client(object):
    def __init__(self, address):
        assert isinstance(address, basestring), address
        self._socket = CONTEXT.socket(zmq.REQ)
        self._socket.connect(address)

    def _call(self, request):
        raw_request = request.SerializeToString()
        self._socket.send(raw_request, 0)
        raw_reply = self._socket.recv(0)
        reply = Response()
        reply.ParseFromString(raw_reply)
        for message in reply.error_log:
            WARN(message)
        if reply.error_log:
            raise ServerError(reply.error_log)
        return reply

    def ping(self):
        request = Request()
        self._call(request)

    def test(self):
        request = Request()
        request.test.SetInParent()
        reply = self._call(request)
        return reply.test.fail_count

    def _simplify(self, codes):
        request = Request()
        request.simplify.SetInParent()
        for code in codes:
            request.simplify.codes.append(code)
        reply = self._call(request)
        return list(reply.simplify.codes)

    def simplify(self, codes):
        assert isinstance(codes, list), codes
        for code in codes:
            assert isinstance(code, basestring), code
        results = self._simplify(codes)
        assert len(results) == len(codes), results
        return results

    def _batch_simplify(self, codes_in, codes_out):
        request = Request()
        request.batch_simplify.SetInParent()
        request.batch_simplify.codes_in = codes_in
        request.batch_simplify.codes_out = codes_out
        reply = self._call(request)
        return reply.batch_simplify.line_count

    def batch_simplify(self, codes_in, codes_out):
        assert isinstance(codes_in, basestring), codes_in
        assert isinstance(codes_out, basestring), codes_out
        with pomagma.util.temp_copy(codes_out) as temp_codes_out:
            line_count = self._batch_simplify(codes_in, temp_codes_out)
        assert os.path.exists(codes_out)
        return line_count

    def _validate(self, codes):
        request = Request()
        request.validate.SetInParent()
        for code in codes:
            request.validate.codes.append(code)
        reply = self._call(request)
        results = []
        for result in reply.validate.results:
            results.append({
                'is_top': TROOL[result.is_top],
                'is_bot': TROOL[result.is_bot],
            })
        return results

    def validate(self, codes):
        assert isinstance(codes, list), codes
        for code in codes:
            assert isinstance(code, basestring), code
        results = self._validate(codes)
        assert len(results) == len(codes), results
        return results
