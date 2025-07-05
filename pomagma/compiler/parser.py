import re
from collections.abc import Iterable
from copy import copy
from typing import Any, TypedDict

from pomagma.compiler.expressions import Expression
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.signature import get_arity, get_nargs

RE_BAR = re.compile("---+")
RE_PADDING = re.compile("   +")
RE_COMMENT = re.compile("#.*$")


class Theory(TypedDict):
    facts: list[Expression]
    rules: list[Sequent]


class ParseError(Exception):
    def __init__(self, message: str, **debuginfo: Any) -> None:
        self.message = str(message)
        self.debuginfo = debuginfo

    def __str__(self) -> str:
        header = ", ".join(
            ["ParseError"]
            + [f"{key} {val}" for key, val in sorted(self.debuginfo.items())]
        )
        return f"{header}: {self.message}"


def find_bars(lines: list[str], **debuginfo: Any) -> list[tuple[int, int, int]]:
    """Find bars in a list of lines. Return a list of tuples (lineno, left, right)."""
    bars: list[tuple[int, int, int]] = []
    for lineno, line in enumerate(lines):
        match = RE_BAR.search(line)
        while match:
            left = match.start()
            right = match.end()
            bars.append((lineno, left, right))
            match = RE_BAR.search(line, right)
            if match and match.start() - right < 3:
                raise ParseError("horizontal rule overlap", lineno=lineno, **debuginfo)
    return bars


def get_spans(
    lines: list[str], linenos: list[int], left: int, right: int, **debuginfo: Any
) -> tuple[int, list[Expression]]:
    """Get spans of expressions between bars."""
    results: list[Expression] = []
    for lineno in linenos:
        debuginfo["lineno"] = lineno
        line = lines[lineno]
        stripped = lines[lineno][left:right].strip()
        if RE_BAR.match(stripped):
            raise ParseError("vertical rule overlap", **debuginfo)
        if stripped:
            for string in RE_PADDING.split(stripped):
                try:
                    expr = parse_string_to_expr(string)
                except Exception as e:
                    raise ParseError(f"{e}\n{line}", **debuginfo)
                results.append(expr)
        else:
            break
    return lineno, results


def parse_lines_to_rules(lines: list[str], **debuginfo: Any) -> list[Sequent]:
    """Parse a list of lines to a list of rules."""
    bars = find_bars(lines, **debuginfo)
    rules: list[Sequent] = []
    for lineno, left, right in bars:
        bar_to_top = list(range(lineno - 1, -1, -1))
        bar_to_bottom = list(range(lineno + 1, len(lines)))
        a, above = get_spans(lines, bar_to_top, left, right, **debuginfo)
        b, below = get_spans(lines, bar_to_bottom, left, right, **debuginfo)
        block = {"top": a + 1, "bottom": b, "left": left, "right": right}
        # print('DEBUG found')
        # for line in lines[block['top']: block['bottom']]:
        #     print('DEBUG'), line[block['left']: block['right']]
        rule = Sequent(above, below)
        debuginfo["block"] = block
        rule.debuginfo = dict(debuginfo)
        rules.append(rule)
    return rules


def erase_rules_from_lines(
    rules: list[Sequent], lines: list[str], **debuginfo: Any
) -> list[str]:
    lines = copy(lines)
    for rule in rules:
        block = rule.debuginfo["block"]
        top = block["top"]
        bottom = block["bottom"]
        left = block["left"]
        right = block["right"]
        for lineno in range(top, bottom):
            line = lines[lineno]
            assert line[left:right].strip(), "nothing to erase"
            lines[lineno] = line[:left] + " " * (right - left) + line[right:]
        for lineno in range(max(0, top - 1), min(len(lines), bottom + 1)):
            debuginfo["lineno"] = lineno
            debuginfo.update(block)
            line = lines[lineno]
            if line[max(0, left - 3) : right + 3].strip():
                raise ParseError("insufficient padding", **debuginfo)
    return lines


def parse_tokens_to_expr(tokens: list[str]) -> Expression:
    """Parse a list of tokens on polish order to an Expression."""
    head = tokens.pop()
    arity = get_arity(head)
    nargs = get_nargs(arity)
    args = [parse_tokens_to_expr(tokens) for _ in range(nargs)]
    return Expression(head, *args)


def parse_string_to_expr(string: str) -> Expression:
    """Parse a string on polish notation to an Expression."""
    tokens = string.strip().split(" ")
    for token in tokens:
        if not token:
            raise ValueError(f"extra whitespace:\n{string!r}")
    tokens.reverse()
    expr = parse_tokens_to_expr(tokens)
    if tokens:
        raise ValueError(f"trailing tokens: {tokens} in:\n{string}")
    return expr


def remove_comments_and_add_padding(lines_with_comments: Iterable[str]) -> list[str]:
    """Remove comments and add padding to a list of lines."""
    lines = [""]
    lines.extend(RE_COMMENT.sub("", line).rstrip() for line in lines_with_comments)
    lines.append("")
    return lines


def parse_lines_to_facts(lines: Iterable[str], **debuginfo: Any) -> list[Expression]:
    """Parse a list of lines to a list of facts."""
    facts: list[Expression] = []
    for lineno, line in enumerate(lines):
        debuginfo["lineno"] = lineno
        line = line.strip()
        if not line:
            continue
        for string in RE_PADDING.split(line):
            try:
                facts.append(parse_string_to_expr(string))
            except Exception as e:
                raise ParseError(str(e), **debuginfo) from e
    return facts


def parse_theory(lines: Iterable[str], **debuginfo: Any) -> Theory:
    """Parse a list of lines to a theory."""
    lines = remove_comments_and_add_padding(lines)
    rules = parse_lines_to_rules(lines, **debuginfo)
    lines = erase_rules_from_lines(rules, lines, **debuginfo)
    facts = parse_lines_to_facts(lines, **debuginfo)
    return {"facts": facts, "rules": rules}


def parse_theory_file(filename: str) -> Theory:
    """Parse a theory file to a theory."""
    with open(filename) as f:
        return parse_theory(f, file=filename)


def parse_theory_string(string: str) -> Theory:
    """Parse a theory string to a theory."""
    return parse_theory(string.splitlines())


def parse_corpus(
    lines: Iterable[str], **debuginfo: Any
) -> dict[Expression, Expression]:
    """Parse a list of lines to a corpus."""
    lines = remove_comments_and_add_padding(lines)
    facts = parse_lines_to_facts(lines, **debuginfo)
    defs: dict[Expression, Expression] = {}
    for fact in facts:
        assert fact.name == "EQUAL", fact
        var, expr = fact.args
        assert var.is_var(), var
        defs[var] = expr
    return defs
