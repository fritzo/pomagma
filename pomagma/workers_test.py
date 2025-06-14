import os

import pomagma.util
import pomagma.workers
from pomagma.util import DB


def test_structure_queue():
    with pomagma.util.in_temp_dir():
        queue = pomagma.workers.FileQueue("test.queue")
        assert not queue.get()
        test_file = DB("test")
        with open(test_file, "w") as f:
            f.write("test")
        assert os.path.exists(test_file)
        queue.push(test_file)
        assert not os.path.exists(test_file)
        assert len(queue) == 1
        assert queue.try_pop(test_file)
        assert os.path.exists(test_file)
        assert len(queue) == 0
