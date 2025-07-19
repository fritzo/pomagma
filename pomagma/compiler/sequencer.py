import heapq
from typing import TypeAlias

from pomagma.compiler import signature
from pomagma.compiler.compiler import GlobalConfig
from pomagma.compiler.util import eval_float53, logger, memoize_arg

Program: TypeAlias = tuple[tuple[str, ...], ...]


def load_lines(filename):
    assert isinstance(filename, str)
    with open(filename) as f:
        for line in f:
            if not line.startswith("#"):
                yield line.strip()


def load_programs(lines: list[str]) -> list[Program]:
    programs: list[Program] = []
    program: list[tuple[str, ...]] = []
    for line in lines:
        if line:
            program.append(tuple(line.split()))
        elif program:
            programs.append(tuple(program))
            program = []
    return programs


def indent_program(program: Program) -> list[str]:
    lines: list[str] = []
    token_position = 0
    indent_until: list[int] = []
    for tokens in program:
        line = " ".join(tokens)
        while indent_until and token_position >= indent_until[-1]:
            indent_until.pop()
        if indent_until:
            line = "  " * len(indent_until) + line
        if tokens[0] == "SEQUENCE":
            end = token_position + eval_float53(int(tokens[1]))
            indent_until.append(end)
        token_position += len(tokens)
        lines.append(line)
    return lines


def dump_programs(programs: list[Program], indent: bool = True) -> list[str]:
    lines: list[str] = []
    for i, program in enumerate(programs):
        lines.append("")
        lines.append(f"# plan {i}: {sizeof_program(program)} bytes")
        if indent:
            lines.extend(indent_program(program))
        else:
            lines.extend(" ".join(line) for line in program)
    return lines


alphabet = "abcdefghijklmnopqrstuvwxyz"


def normalize_alpha(program: Program) -> Program:
    rename: dict[str, str] = {}
    for line in program:
        for token in line[1:]:
            if signature.is_var(token):
                rename.setdefault(token, alphabet[len(rename)])
    return tuple(tuple(rename.get(token, token) for token in line) for line in program)


def extract_block(program: Program) -> Program:
    result = list(program)
    while result and result[-1][0] != "IF_BLOCK":
        result.pop()
    return tuple(result)


def are_compatible_v2(program1: Program, program2: Program) -> bool:
    if program1[0] != program2[0]:
        return False
    if program1[0] == ("FOR_BLOCK",):
        if extract_block(program1) != extract_block(program2):
            return False
    return True


# DEPRECATED
def are_compatible(program1: Program, program2: Program) -> bool:
    head1 = program1[0]
    head2 = program2[0]
    if head1[0].startswith("GIVEN") or head2[0].startswith("GIVEN"):
        return head1 == head2
    if head1[0] == "FOR_BLOCK" or head2[0] == "FOR_BLOCK":
        return False
    return head1 == head2


def count_overlap(program1: Program, program2: Program) -> int:
    result = 0
    for line1, line2 in zip(program1, program2, strict=False):
        if line1 != line2:
            break
        result += 1
    return result


def sizeof_program(program: Program) -> int:
    return sum(len(line) for line in program)


def get_jump(jump_size: int) -> tuple[int, int]:
    jump = 0
    while eval_float53(jump) < jump_size:
        jump += 1
    assert jump < 256, f"jump out of range: {jump_size}"
    padding = eval_float53(jump) - jump_size
    return jump, padding


def merge_programs(program1: Program, program2: Program) -> Program:
    assert program1 != program2, "duplicate"
    if sizeof_program(program1) > sizeof_program(program2):
        program1, program2 = program2, program1
    program: list[tuple[str, ...]] = []
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


_EXPENSIVE_OPCODES: tuple[str, ...] = (
    "FOR_BINARY_FUNCTION_LHS_VAL",
    "FOR_BINARY_FUNCTION_RHS_VAL",
    "FOR_BINARY_FUNCTION_VAL",
    "FOR_SYMMETRIC_FUNCTION_LHS_VAL",
    "FOR_SYMMETRIC_FUNCTION_VAL",
)


def is_nless_monotone_program(program):
    """Detect expensive NLESS monotonicity programs."""
    if len(program) != 4:
        return False
    if program[0][:2] != ("GIVEN_BINARY_RELATION", "NLESS"):
        return False
    if program[1][0] not in _EXPENSIVE_OPCODES:
        return False
    if program[2][0] not in _EXPENSIVE_OPCODES:
        return False
    if program[3][:2] != ("INFER_BINARY_RELATION", "NLESS"):
        return False
    return True


def add_nless_conditionals(programs):
    """Add IF_GLOBAL conditionals to NLESS monotonicity programs."""
    result = []
    for program in programs:
        if is_nless_monotone_program(program):
            program = (
                program[0],
                ("IF_GLOBAL", str(GlobalConfig.ENABLE_NLESS_MONOTONE)),
                *program[1:],
            )
        result.append(program)
    return result


def optimize(lines):
    programs = sorted(set(map(normalize_alpha, load_programs(lines))))
    programs = add_nless_conditionals(programs)
    programs = MergeProcessor(programs).run()
    return dump_programs(programs)
