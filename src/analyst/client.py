import sys
import zmq
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
        return '\n'.join(['Server Errors:'] + self.messages)


class Client(object):

    def __init__(self, address):
        assert isinstance(address, basestring), address
        self._socket = CONTEXT.socket(zmq.REQ)
        print 'connecting to analyst at', address
        self._socket.connect(address)

    def _call(self, request):
        raw_request = request.SerializeToString()
        self._socket.send(raw_request, 0)
        raw_reply = self._socket.recv(0)
        reply = Response()
        reply.ParseFromString(raw_reply)
        for message in reply.error_log:
            WARN(message)
        for key, val in request.ListFields():
            assert reply.HasField(key.name), key.name
        if reply.error_log:
            raise ServerError(reply.error_log)
        return reply

    def ping(self):
        request = Request()
        self._call(request)

    def ping_id(self, id):
        assert isinstance(id, basestring), id
        request = Request()
        request.id = id
        reply = self._call(request)
        return reply.id

    def test_inference(self):
        request = Request()
        request.test_inference.SetInParent()
        reply = self._call(request)
        return reply.test_inference.fail_count

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

    def _validate_corpus(self, lines):
        request = Request()
        request.validate_corpus.SetInParent()
        for line in lines:
            request_line = request.validate_corpus.lines.add()
            name = line['name']
            if name:
                request_line.name = name
            request_line.code = line['code']
        reply = self._call(request)
        results = []
        for result in reply.validate_corpus.results:
            results.append({
                'is_top': TROOL[result.is_top],
                'is_bot': TROOL[result.is_bot],
                'pending': result.pending,
            })
        return results

    def validate_corpus(self, lines):
        assert isinstance(lines, list), lines
        for line in lines:
            assert isinstance(line, dict), line
            assert sorted(line.keys()) == ['code', 'name']
            name = line['name']
            assert name is None or isinstance(name, basestring), name
            code = line['code']
            assert isinstance(code, basestring), code
        results = self._validate_corpus(lines)
        assert len(results) == len(lines), results
        return results

    def get_histogram(self):
        request = Request()
        request.get_histogram.SetInParent()
        reply = self._call(request)
        obs = {}
        symbols = {}
        for term in reply.get_histogram.histogram.terms:
            assert bool(term.ob) != bool(term.name), term
            count = int(term.count)
            if term.ob:
                obs[int(term.ob)] = count
            else:
                symbols[str(term.name)] = count
        result = {'obs': obs, 'symbols': symbols}
        return result

    def _fit_language(self, histogram=None):
        request = Request()
        request.fit_language.SetInParent()
        if histogram is not None:
            terms = request.fit_language.histogram.terms
            for name, count in histogram['symbols'].iteritems():
                term = terms.add()
                term.name = name
                term.count = count
            for ob, count in histogram['obs'].iteritems():
                term = terms.add()
                term.ob = ob
                term.count = count
        reply = self._call(request)
        result = {}
        for symbol in reply.fit_language.symbols:
            name = str(symbol.name)
            prob = float(symbol.prob)
            result[name] = prob
        return result

    def fit_language(self, histogram=None):
        if histogram is not None:
            assert isinstance(histogram, dict), histogram
            keys = set(histogram.keys())
            assert keys == set(['symbols', 'obs']), keys
            for name, count in histogram['symbols'].iteritems():
                assert isinstance(name, str), name
                assert isinstance(count, int), count
            for ob, count in histogram['obs'].iteritems():
                assert isinstance(ob, int), ob
                assert isinstance(count, int), count
        return self._fit_language(histogram)
