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
        print 'connecting to cartographer at', address
        self._socket.connect(address)

    def _call(self, request):
        raw_request = request.SerializeToString()
        self._socket.send(raw_request, 0)
        raw_reply = self._socket.recv(0)
        reply = Response()
        reply.ParseFromString(raw_reply)
        for key, val in request.ListFields():
            assert reply.HasField(key.name), key.name
        return reply

    def ping(self):
        request = Request()
        self._call(request)

    def _trim(self, tasks):
        request = Request()
        for task in tasks:
            request_task = request.trim.add()
            request_task.size = task['size']
            request_task.temperature = task['temperature']
            request_task.filename = task['filename']
        self._call(request)

    def trim(self, tasks):
        assert isinstance(tasks, list)
        for task in tasks:
            assert isinstance(task, dict)
        tasks = [task.copy() for task in tasks]
        for task in tasks:
            assert 'size' in task, task
            assert isinstance(task['size'], int), task['size']
            assert 'filename' in task, task
            assert isinstance(task['filename'], basestring), task['filename']
            temperature = task.setdefault('temperature', 1)
            assert temperature in [0, 1], temperature
        filenames = [task['filename'] for task in tasks]
        assert len(filenames) == len(set(filenames)), 'duplicated out file'
        with pomagma.util.temp_copies(filenames) as temp_filenames:
            for task, filename in zip(tasks, temp_filenames):
                task['filename'] = filename
            self._trim(tasks)
        for filename in filenames:
            assert os.path.exists(filename), filename

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
        reply = self._call(request)
        return {
            'pos': reply.assume.pos_count,
            'neg': reply.assume.neg_count,
            'merge': reply.assume.merge_count,
        }

    def assume(self, facts_in):
        assert isinstance(facts_in, basestring), facts_in
        assert os.path.exists(facts_in), facts_in
        return self._assume(facts_in)

    def _infer(self, priority):
        request = Request()
        request.infer.SetInParent()
        request.infer.priority = priority
        reply = self._call(request)
        return reply.infer.theorem_count

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
        reply = self._call(request)
        return {
            'diverge_count': reply.conjecture.diverge_count,
            'equal_count': reply.conjecture.equal_count,
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

    def info(self):
        request = Request()
        request.info.SetInParent()
        reply = self._call(request)
        info = reply.info
        return {
            'item_count': info.item_count,
        }

    def stop(self):
        request = Request()
        request.stop.SetInParent()
        self._call(request)
