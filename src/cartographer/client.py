import os
import zmq
from pomagma.cartographer import messages_pb2 as messages


Request = messages.CartographerRequest
Response = messages.CartographerResponse

CONTEXT = zmq.Context()


class Client(object):
    def __init__(self, address):
        assert isinstance(address, basestring), address
        self._socket = CONTEXT.socket(zmq.REQ)
        self._socket.connect(address)

    def _call(self, request):
        raw_request = request.SerializeToString()
        self._socket.send(raw_request, 0)
        raw_response = self._socket.recv(0)
        response = Response()
        response.ParseFromString(raw_response)
        return response

    def ping(self):
        request = Request()
        self._call(request)

    def _trim(self, region_size, regions_out):
        request = Request()
        request.trim.SetInParent()
        request.trim.region_size = region_size
        for region in regions_out:
            request.trim.regions_out.append(region)
        self._call(request)

    def trim(self, region_size, regions_out):
        assert isinstance(region_size, int), region_size
        assert isinstance(regions_out, list), regions_out
        for region in regions_out:
            assert isinstance(region, basestring), region
            assert os.path.exists(os.path.dirname(os.path.abspath(region)))
            assert not os.path.exists(region)
        self._trim(region_size, regions_out)
        for region in regions_out:
            assert os.path.exists(region)

    def _aggregate(self, surveys_in):
        request = Request()
        request.aggregate.SetInParent()
        for survey in surveys_in:
            request.aggregate.surveys_in.append(survey)
        self._call(request)

    def aggregate(self, surveys_in):
        assert isinstance(surveys_in, list)
        for survey in surveys_in:
            assert isinstance(survey, basestring), survey
            assert os.path.exists(survey)
        self._aggregate(surveys_in)

    def infer(self):
        request = Request()
        request.infer.SetInParent()
        response = self._call(request)
        return response.infer.theorem_count

    def crop(self):
        request = Request()
        request.crop.SetInParent()
        self._call(request)

    def validate(self):
        request = Request()
        request.validate.SetInParent()
        self._call(request)

    def _dump(self, world_out):
        request = Request()
        request.dump.SetInParent()
        request.dump.world_out = world_out
        self._call(request)

    def dump(self, world_out):
        assert isinstance(world_out, basestring), world_out
        dirname, filename = os.path.split(world_out)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        pid = os.getpid()
        temp_out = os.path.join(dirname, 'temp.{}.{}'.format(pid, filename))
        self._dump(temp_out)
        assert os.path.exists(temp_out), temp_out
        os.rename(temp_out, world_out)
