import sys
import time

import zmq

from pomagma.analyst import analyst_messages_pb2 as messages
from pomagma.analyst import compiler

CONTEXT = zmq.Context()
POLL_TIMEOUT_MS = 1000
VALIDATE_POLL_SEC = 0.1
Request = messages.AnalystRequest
Response = messages.AnalystResponse

TROOL = {
    Response.MAYBE: None,
    Response.TRUE: True,
    Response.FALSE: False,
}


def WARN(message):
    sys.stdout.write(f"WARNING {message}\n")
    sys.stdout.flush()


class ServerError(Exception):
    def __init__(self, messages):
        self.messages = list(messages)

    def __str__(self):
        return "\n".join(["Server Errors:", *self.messages])


class Client:
    def __init__(self, address, poll_callback=None):
        assert isinstance(address, str), address
        assert poll_callback is None or callable(poll_callback), poll_callback
        self._poll_callback = poll_callback
        self._socket = CONTEXT.socket(zmq.REQ)
        print("connecting to analyst at", address)
        self._socket.connect(address)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._socket.close()

    def _call(self, request):
        raw_request = request.SerializeToString()
        self._socket.send(raw_request, 0)
        if self._poll_callback is not None:
            while not self._socket.poll(timeout=POLL_TIMEOUT_MS):
                self._poll_callback()
        raw_reply = self._socket.recv(0)
        reply = Response()
        reply.ParseFromString(raw_reply)
        for message in reply.error_log:
            WARN(message)
        for key, val in request.ListFields():
            # Handle different field types for proto3 compatibility
            if key.name == "id":
                # For id field (scalar string), verify response id matches request id
                assert reply.id == val, (
                    f"Response id '{reply.id}' != request id '{val}'"
                )
            elif key.name == "error_log":
                # repeated field, always present in proto3, skip validation
                pass
            else:
                # For message fields, HasField still works in proto3
                assert reply.HasField(key.name), key.name
        if reply.error_log:
            raise ServerError(reply.error_log)
        return reply

    def ping(self):
        request = Request()
        self._call(request)

    def ping_id(self, id):
        assert isinstance(id, str), id
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
            request.simplify.codes.append(compiler.desugar(code))
        reply = self._call(request)
        return list(reply.simplify.codes)

    def simplify(self, codes):
        assert isinstance(codes, list), codes
        for code in codes:
            assert isinstance(code, str), code
        results = self._simplify(codes)
        assert len(results) == len(codes), results
        return list(map(str, results))

    def _solve(self, var, theory, max_solutions):
        request = Request()
        request.solve.program = compiler.compile_solver(var, theory)
        if max_solutions is not None:
            request.solve.max_solutions = max_solutions
        reply = self._call(request)
        return {
            "necessary": list(map(str, reply.solve.necessary)),
            "possible": list(map(str, reply.solve.possible)),
        }

    def solve(self, var, theory, max_solutions=None):
        assert isinstance(var, str), var
        assert isinstance(theory, str), theory
        if max_solutions is not None:
            assert isinstance(max_solutions, int | float), max_solutions
        solutions = self._solve(var, theory, max_solutions)
        assert not (set(solutions["necessary"]) & set(solutions["possible"]))
        if max_solutions is not None:
            count = len(solutions["necessary"]) + len(solutions["possible"])
            assert count <= max_solutions, solutions
        return solutions

    def _validate(self, codes):
        request = Request()
        request.validate.SetInParent()
        for code in codes:
            request.validate.codes.append(code)
        reply = self._call(request)
        return [
            {
                "is_top": TROOL[result.is_top],
                "is_bot": TROOL[result.is_bot],
            }
            for result in reply.validate.results
        ]

    def validate(self, codes):
        assert isinstance(codes, list), codes
        for code in codes:
            assert isinstance(code, str), code
        results = self._validate(codes)
        assert len(results) == len(codes), results
        return results

    def _validate_corpus(self, lines):
        request = Request()
        request.validate_corpus.SetInParent()
        for line in lines:
            request_line = request.validate_corpus.lines.add()
            name = line["name"]
            if name:
                request_line.name = name
            request_line.code = line["code"]
        reply = self._call(request)
        return [
            {
                "is_top": TROOL[result.is_top],
                "is_bot": TROOL[result.is_bot],
                "pending": result.pending,
            }
            for result in reply.validate_corpus.results
        ]

    def validate_corpus(self, lines):
        assert isinstance(lines, list), lines
        for line in lines:
            assert isinstance(line, dict), line
            assert sorted(line.keys()) == ["code", "name"]
            name = line["name"]
            assert name is None or isinstance(name, str), name
            code = line["code"]
            assert isinstance(code, str), code
        results = self._validate_corpus(lines)
        assert len(results) == len(lines), results
        return results

    def validate_facts(self, facts, block=True):
        assert isinstance(facts, list), facts
        request = Request()
        request.validate_facts.SetInParent()
        for fact in facts:
            assert isinstance(fact, str), fact
            request.validate_facts.facts.append(compiler.desugar(fact))
        reply = self._call(request)
        while block and reply.validate_facts.result == Response.MAYBE:
            time.sleep(VALIDATE_POLL_SEC)
            reply = self._call(request)
        return TROOL[reply.validate_facts.result]

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
        return {"obs": obs, "symbols": symbols}

    def _fit_language(self, histogram=None):
        request = Request()
        request.fit_language.SetInParent()
        if histogram is not None:
            terms = request.fit_language.histogram.terms
            for name, count in list(histogram["symbols"].items()):
                term = terms.add()
                term.name = name
                term.count = count
            for ob, count in list(histogram["obs"].items()):
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
            assert keys == {"symbols", "obs"}, keys
            for name, count in list(histogram["symbols"].items()):
                assert isinstance(name, str), name
                assert isinstance(count, int), count
            for ob, count in list(histogram["obs"].items()):
                assert isinstance(ob, int), ob
                assert isinstance(count, int), count
        return self._fit_language(histogram)
