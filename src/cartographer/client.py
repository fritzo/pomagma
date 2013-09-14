import os
import zmq
from pomagma.cartographer import messages_pb2 as messages


Request = messages.CartographerRequest
Response = messages.CartographerResponse

CONTEXT = zmq.Context()


class Client(object):
    def __init__(self, address):
        self._socket = CONTEXT.socket(zmq.REQ)
        self._socket.connect(address)

    def _call(self, request):
        raw_request = request.toByteArray()
        self._socket.send(raw_request, 0)
        raw_response = self._socket.recv(0)
        response = Response.ParseFromString(raw_response)
        return response

    def ping(self):
        request = Request()
        self._call(request)

    def _trim(self, size, regions_out):
        request = Request()
        request.trim = Request.Trim()
        request.trim.size = size
        for region in regions_out:
            request.regions_out.add(region)
        self._call(request)

    def trim(self, size, regions_out):
        assert regions_out
        for region in regions_out:
            assert os.path.exists(os.path.dirname(os.path.abspath(region)))
            assert not os.path.exists(region)
        self._trim(self, size, regions_out)
        for region in regions_out:
            assert os.path.exists(region)

    def _aggregate(self, surveys_in):
        request = Request()
        request.aggregate = Request.Aggregate()
        for survey in surveys_in:
            request.aggregate.surveys_in.add(survey)
        self._call(request)

    def aggregate(self, surveys_in):
        assert surveys_in
        for survey in surveys_in:
            assert os.path.exists(surveys_in)
        self._aggregate(surveys_in)

    def infer(self):
        request = Request()
        request.infer = Request.Infer()
        response = self._call(request)
        return response.theorem_count

    def validate(self):
        request = Request()
        request.validate = Request.Validate()
        self._call(request)

    def _dump(self, world_out):
        request = Request()
        request.dump = Request.Dump()
        request.dump.world_out = world_out
        self._call(request)

    def dump(self, world_out):
        assert os.path.exists(os.path.dirname(os.path.abspath(world_out)))
        assert not os.path.exists(world_out)
        self._dump(world_out)
        assert os.path.exists(world_out)
