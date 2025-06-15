import heapq

from pomagma.compiler import signature
from pomagma.compiler.util import eval_float53, logger, memoize_arg


def load_lines(filename):
    assert isinstance(filename, str)
    with open(filename) as f:
        for line in f:
            if not line.startswith("#"):
                yield line.strip()


def load_programs(lines):
    programs = []
    program = []
    for line in lines:
        if line:
            program.append(tuple(line.split()))
        elif program:
            programs.append(tuple(program))
            program = []
    return programs


def dump_programs(programs):
    lines = []
    for i, program in enumerate(programs):
        lines.append("")
        lines.append(f"# plan {i}: {sizeof_program(program)} bytes")
        lines.extend(" ".join(line) for line in program)
    return lines


alphabet = "abcdefghijklmnopqrstuvwxyz"


def normalize_alpha(program):
    rename = {}
    for line in program:
        for token in line[1:]:
            if signature.is_var(token):
                rename.setdefault(token, alphabet[len(rename)])
    return tuple(tuple(rename.get(token, token) for token in line) for line in program)


def are_compatible(program1, program2):
    head1 = program1[0]
    head2 = program2[0]
    if head1[0].startswith("GIVEN") or head2[0].startswith("GIVEN"):
        return head1 == head2
    if head1[0] == "FOR_BLOCK" or head2[0] == "FOR_BLOCK":
        return False
    return head1 == head2


def count_overlap(program1, program2):
    result = 0
    for line1, line2 in zip(program1, program2):
        if line1 != line2:
            break
        result += 1
    return result


def sizeof_program(program):
    return sum(len(line) for line in program)


def get_jump(jump_size):
    jump = 0
    while eval_float53(jump) < jump_size:
        jump += 1
    assert jump < 256, f"jump out of range: {jump_size}"
    padding = eval_float53(jump) - jump_size
    return jump, padding


def merge_programs(program1, program2):
    assert program1 != program2, "duplicate"
    if sizeof_program(program1) > sizeof_program(program2):
        program1, program2 = program2, program1
    program = []
    for i in range(min(len(program1), len(program2))):
        if program1[i] != program2[i]:
            break
        program.append(program1[i])
    logger("saved {} operations by merging", i)
    program1 = program1[i:]
    program2 = program2[i:]
    assert program1 and program2
    jump, padding = get_jump(sizeof_program(program1))
    program.append(("SEQUENCE", str(jump)))
    program += list(program1)
    program += [("PADDING",)] * padding
    program += list(program2)
    return tuple(program)


@memoize_arg
def program_order(program):
    token = program[0][0]
    return token.startswith("GIVEN"), token == "FOR_BLOCK", program


class MergeProcessor:
    def __init__(self, programs):
        programs = list(map(tuple, programs))
        programs.sort(key=program_order)
        self._programs = dict(enumerate(programs))
        self._prev = {}
        self._next = {}
        self._tasks = []
        count = len(programs)
        self._id = count
        for id1, id2 in zip(list(range(count - 1)), list(range(1, count))):
            self.add_task(id1, id2)

    def get_id(self):
        result = self._id
        self._id += 1
        return result

    def add_task(self, id1, id2):
        program1 = self._programs[id1]
        program2 = self._programs[id2]
        if are_compatible(program1, program2):
            self._prev[id2] = id1
            self._next[id1] = id2
            size = sizeof_program(program1) + sizeof_program(program2)
            overlap = count_overlap(program1, program2)
            # Sort tasks by most overlap and largest program
            task = (-overlap, -size), id1, id2
            heapq.heappush(self._tasks, task)

    def process_tasks(self):
        logger("processing {} merge tasks", len(self._tasks))
        while self._tasks:
            _, id1, id2 = heapq.heappop(self._tasks)
            if id1 in self._programs and id2 in self._programs:
                yield id1, id2

    def run(self):
        for id1, id2 in self.process_tasks():
            program1 = self._programs.pop(id1)
            program2 = self._programs.pop(id2)
            program = merge_programs(program1, program2)
            # print('DEBUG'), '; '.join(map(' '.join, program))
            # print('DEBUG'), '-' * 70
            # print('\n').join(map(' '.join, program))
            id = self.get_id()
            self._programs[id] = program
            actual = self._prev.pop(id2)
            assert actual == id1
            actual = self._next.pop(id1)
            assert actual == id2
            if id1 in self._prev:
                id0 = self._prev.pop(id1)
                actual = self._next.pop(id0)
                assert actual == id1
                self.add_task(id0, id)
            if id2 in self._next:
                id3 = self._next.pop(id2)
                actual = self._prev.pop(id3)
                assert actual == id2
                self.add_task(id, id3)
        assert not self._tasks, self._tasks
        assert not self._prev, self._prev
        assert not self._next, self._next
        programs = list(self._programs.values())
        programs.sort(key=program_order)
        return programs


def optimize(lines):
    programs = sorted(set(map(normalize_alpha, load_programs(lines))))
    programs = MergeProcessor(programs).run()
    return dump_programs(programs)
