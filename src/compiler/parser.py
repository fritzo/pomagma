import re
from copy import copy
from pomagma.compiler.expressions import Expression
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.signature import get_arity
from pomagma.compiler.signature import get_nargs


RE_BAR = re.compile('---+')
RE_PADDING = re.compile('   +')
RE_COMMENT = re.compile('#.*$')


class ParseError(Exception):

    def __init__(self, message, **debuginfo):
        self.message = str(message)
        self.debuginfo = debuginfo

    def __str__(self):
        header = ', '.join(['ParseError'] + [
            '{} {}'.format(key, val)
            for key, val in sorted(self.debuginfo.iteritems())
        ])
        return '{}: {}'.format(header, self.message)


def find_bars(lines, **debuginfo):
    bars = []
    for lineno, line in enumerate(lines):
        match = RE_BAR.search(line)
        while match:
            left = match.start()
            right = match.end()
            bars.append((lineno, left, right))
            match = RE_BAR.search(line, right)
            if match and match.start() - right < 3:
                raise ParseError(
                    'horizontal rule overlap', lineno=lineno, **debuginfo)
    return bars


def get_spans(lines, linenos, left, right, **debuginfo):
    results = []
    for lineno in linenos:
        debuginfo['lineno'] = lineno
        line = lines[lineno]
        stripped = lines[lineno][left: right].strip()
        if RE_BAR.match(stripped):
            raise ParseError('vertical rule overlap', **debuginfo)
        if stripped:
            for string in RE_PADDING.split(stripped):
                try:
                    expr = parse_string_to_expr(string)
                except Exception as e:
                    raise ParseError('{}\n{}'.format(e, line), **debuginfo)
                results.append(expr)
        else:
            break
    return lineno, results


def parse_lines_to_rules(lines, **debuginfo):
    bars = find_bars(lines, **debuginfo)
    rules = []
    for lineno, left, right in bars:
        bar_to_top = xrange(lineno - 1, -1, -1)
        bar_to_bottom = xrange(lineno + 1, len(lines))
        a, above = get_spans(lines, bar_to_top, left, right, **debuginfo)
        b, below = get_spans(lines, bar_to_bottom, left, right, **debuginfo)
        block = {'top': a + 1, 'bottom': b, 'left': left, 'right': right}
        # print 'DEBUG found'
        # for line in lines[block['top']: block['bottom']]:
        #     print 'DEBUG', line[block['left']: block['right']]
        rule = Sequent(above, below)
        debuginfo['block'] = block
        rule.debuginfo = dict(debuginfo)
        rules.append(rule)
    return rules


def erase_rules_from_lines(rules, lines, **debuginfo):
    lines = copy(lines)
    for rule in rules:
        block = rule.debuginfo['block']
        top = block['top']
        bottom = block['bottom']
        left = block['left']
        right = block['right']
        for lineno in range(top, bottom):
            line = lines[lineno]
            assert line[left: right].strip(), 'nothing to erase'
            lines[lineno] = line[:left] + ' ' * (right - left) + line[right:]
        for lineno in range(max(0, top - 1), min(len(lines), bottom + 1)):
            debuginfo['lineno'] = lineno
            debuginfo.update(block)
            line = lines[lineno]
            if line[max(0, left - 3): right + 3].strip():
                raise ParseError('insufficient padding', **debuginfo)
    return lines


def parse_tokens_to_expr(tokens):
    head = tokens.pop()
    arity = get_arity(head)
    nargs = get_nargs(arity)
    args = [parse_tokens_to_expr(tokens) for _ in xrange(nargs)]
    return Expression.make(head, *args)


def parse_string_to_expr(string):
    tokens = string.strip().split(' ')
    for token in tokens:
        if not token:
            raise ValueError('extra whitespace:\n{}'.format(repr(string)))
    tokens.reverse()
    expr = parse_tokens_to_expr(tokens)
    if tokens:
        raise ValueError('trailing tokens: {} in:\n{}'.format(tokens, string))
    return expr


def parse_file_to_lines(filename):
    lines = ['']
    with open(filename) as f:
        for line in f:
            lines.append(RE_COMMENT.sub('', line.rstrip()))
    lines.append('')
    return lines


def parse_lines_to_facts(lines, **debuginfo):
    facts = []
    for lineno, line in enumerate(lines):
        debuginfo['lineno'] = lineno
        line = line.strip()
        if line:
            for string in RE_PADDING.split(line):
                try:
                    facts.append(parse_string_to_expr(string))
                except Exception as e:
                    raise ParseError(e, **debuginfo)
    return facts


def parse_facts(filename):
    lines = parse_file_to_lines(filename)
    return parse_lines_to_facts(lines, file=filename)


def parse_theory(filename):
    lines = parse_file_to_lines(filename)
    rules = parse_lines_to_rules(lines, file=filename)
    lines = erase_rules_from_lines(rules, lines, file=filename)
    facts = parse_lines_to_facts(lines, file=filename)
    return {'facts': facts, 'rules': rules}
