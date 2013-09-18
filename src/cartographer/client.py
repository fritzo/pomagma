import os
import zmq
import pomagma.util
from pomagma.cartographer import messages_pb2 as messages


CONTEXT = zmq.Context()

Request = messages.CartographerRequest
Response = messages.CartographerResponse


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

    def _trim(self, region_size, regions_out, temperature):
        request = Request()
        request.trim.SetInParent()
        request.trim.temperature = temperature
        request.trim.region_size = region_size
        for region in regions_out:
            request.trim.regions_out.append(region)
        self._call(request)

    def trim(self, region_size, regions_out, temperature=1):
        assert isinstance(region_size, int), region_size
        assert isinstance(regions_out, list), regions_out
        assert isinstance(temperature, int), temperature
        for region in regions_out:
            assert isinstance(region, basestring), region
            assert not os.path.exists(region), region
        with pomagma.util.temp_copies(regions_out) as temp_regions_out:
            self._trim(region_size, temp_regions_out, temperature)
        for region in regions_out:
            assert os.path.exists(region), region

    def _aggregate(self, survey_in):
        request = Request()
        request.aggregate.SetInParent()
        request.aggregate.survey_in = survey_in
        self._call(request)

    def aggregate(self, survey_in):
        assert isinstance(survey_in, basestring), survey_in
        assert os.path.exists(survey_in), survey_in
        self._aggregate(survey_in)

    def _assume(self, facts_in):
        request = Request()
        request.assume.SetInParent()
        request.assume.facts_in = facts_in
        response = self._call(request)
        return {
            'pos': response.assume.pos_count,
            'neg': response.assume.neg_count,
            'merge': response.assume.merge_count,
        }

    def assume(self, facts_in):
        assert isinstance(facts_in, basestring), facts_in
        assert os.path.exists(facts_in), facts_in
        return self._assume(facts_in)

    def _infer(self, priority):
        request = Request()
        request.infer.SetInParent()
        request.infer.priority = priority
        response = self._call(request)
        return response.infer.theorem_count

    def infer(self, priority):
        assert isinstance(priority, int), priority
        assert priority in [0, 1], priority
        return self._infer(priority)

    def normalize(self):
        for priority in [0, 1]:
            while self.infer(priority):
                pass

    def _conjecture(self, diverge_out, equal_out, max_count):
        request = Request()
        request.conjecture.SetInParent()
        request.conjecture.diverge_out = diverge_out
        request.conjecture.equal_out = equal_out
        request.conjecture.max_count = max_count
        response = self._call(request)
        return {
            'diverge_count': response.conjecture.diverge_count,
            'equal_count': response.conjecture.equal_count,
        }

    def conjecture(self, diverge_out, equal_out, max_count=1000):
        assert isinstance(diverge_out, basestring), diverge_out
        assert isinstance(equal_out, basestring), equal_out
        assert isinstance(max_count, int)
        assert max_count > 0
        with pomagma.util.temp_copy(diverge_out) as temp_diverge_out:
            with pomagma.util.temp_copy(equal_out) as temp_equal_out:
                counts = self._conjecture(
                    temp_diverge_out,
                    temp_equal_out,
                    max_count)
        assert os.path.exists(diverge_out), diverge_out
        assert os.path.exists(equal_out), equal_out
        return counts

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
        assert os.path.exists(os.path.dirname(os.path.abspath(world_out)))
        with pomagma.util.temp_copy(world_out) as temp_world_out:
            self._dump(temp_world_out)
        assert os.path.exists(world_out), world_out
