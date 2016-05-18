import zmq
from google.protobuf.descriptor import FieldDescriptor
from pomagma.reducer import messages_pb2 as messages


CONTEXT = zmq.Context()
POLL_TIMEOUT_MS = 1000
Request = messages.ReducerRequest
Response = messages.ReducerResponse


class Client(object):

    def __init__(self, address, poll_callback):
        assert isinstance(address, basestring), address
        assert callable(poll_callback), poll_callback
        self._poll_callback = poll_callback
        self._socket = CONTEXT.socket(zmq.REQ)
        print 'connecting to cartographer at', address
        self._socket.connect(address)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._socket.close()

    def _call(self, request):
        raw_request = request.SerializeToString()
        self._socket.send(raw_request, 0)
        while not self._socket.poll(timeout=POLL_TIMEOUT_MS):
            self._poll_callback()
        raw_reply = self._socket.recv(0)
        reply = Response()
        reply.ParseFromString(raw_reply)
        for field in Request.DESCRIPTOR.fields:
            if field.label == FieldDescriptor.LABEL_OPTIONAL:
                expected = request.HasField(field.name)
                actual = reply.HasField(field.name)
                assert actual == expected, field.name
            elif field.label == FieldDescriptor.LABEL_REPEATED:
                expected = len(getattr(request, field.name))
                actual = len(getattr(reply, field.name))
                assert actual == expected, field.name
        return reply

    def ping(self):
        request = Request()
        self._call(request)

    def validate(self):
        request = Request()
        request.validate.SetInParent()
        reply = self._call(request)
        if reply.valid:
            return True, []
        else:
            return False, [str(error) for error in reply.errors]

    def reset(self):
        request = Request()
        request.reset.SetInParent()
        self._call(request)

    def reduce(self, code, budget=0):
        assert isinstance(code, basestring), code
        assert isinstance(budget, int), budget
        assert budget >= 0, budget
        request = Request()
        request.reduce.code = code
        request.reduce.budget = budget
        reply = self._call(request)
        if not reply.code:
            raise ValueError('Invalid code: {}'.format(code))
        return {'code': str(reply.code), 'budget': int(reply.budget)}

    def stop(self):
        request = Request()
        request.stop.SetInParent()
        self._call(request)
