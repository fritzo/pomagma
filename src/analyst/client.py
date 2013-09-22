import os
import zmq
import pomagma.util
from pomagma.analyst import messages_pb2 as messages


CONTEXT = zmq.Context()

Request = messages.AnalystRequest
Response = messages.AnalystResponse

TROOL = {
    Response.Validate.Validity.TRUE: True,
    Response.Validate.Validity.FALSE: False,
    Response.Validate.Validity.MAYBE: None,
}


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
            request.simplify.add(code)
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

    def validate(self, corpus):
        assert isinstance(corpus, list)
        request = Request()
        request.validate.SetInParent()
        for line in corpus:
            request_line = request.validate.corpus.add()
            assert isinstance(line, dict)
            code = line['code']
            assert isinstance(code, basestring), code
            request_line.code = code
            if 'name' in line:
                name = line['name']
                assert isinstance(name, basestring), name
                request_line.name = name
        reply = self._call(request)
        assert len(reply.validate.results) == len(corpus)
        results = []
        for result in reply.validate.results:
            results.append({
                'is_top': TROOL[result.is_top],
                'is_bot': TROOL[result.is_bot],
            })
        return results
