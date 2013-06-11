import re
from pomagma.compiler.signature import get_arity, get_nargs
from pomagma.compiler.expressions import Expression
from pomagma.compiler.sequents import Sequent


RE_BAR = re.compile('---+')
RE_PADDING = re.compile('   +')
RE_COMMENT = re.compile('#.*$')


class ParseError(Exception):

    def __init__(self, message, lineno='unknown'):
        self.message = str(message)
        self.lineno = lineno

    def __str__(self):
        return 'ParseError on line {0}: {1}'.format(self.lineno, self.message)


def find_bars(lines):
    bars = []
    for lineno, line in enumerate(lines):
        match = RE_BAR.search(line)
        while match:
            left = match.start()
            right = match.end()
            bars.append((lineno, left, right))
            match = RE_BAR.search(line, right)
            if match and match.start() - right < 3:
                raise ParseError('horizontal rule overlap', lineno)
    return bars


def get_spans(lines, linenos, left, right):
    results = []
    for lineno in linenos:
        line = lines[lineno]
        section = lines[lineno][left:right]
        stripped = section.strip()
        if RE_BAR.match(stripped):
            raise ParseError('vertical rule overlap', lineno)
        if stripped:
            for string in RE_PADDING.split(stripped):
                try:
                    expr = parse_string_to_expr(string)
                except Exception as e:
                    raise ParseError('{0}\n{1}'.format(e, line), lineno)
                results.append(expr)
        else:
            break
    return lineno, results


def parse_lines_to_rules(lines, filename):
    lines = list(lines)
    bars = find_bars(lines)
    rules = []
    for lineno, left, right in bars:
        bar_to_top = xrange(lineno - 1, -1, -1)
        bar_to_bottom = xrange(lineno + 1, len(lines))
        a, above = get_spans(lines, bar_to_top, left, right)
        b, below = get_spans(lines, bar_to_bottom, left, right)
        block = {'top': a - 1, 'bottom': b, 'left': left, 'right': right}
        rule = Sequent(above, below)
        rule.debuginfo = {'file': filename, 'block': block}
        rules.append(rule)
    return rules


def check_whitespace(lines, rules):
    lines = list(lines)
    for rule in rules:
        block = rule.debuginfo['block']
        top = block['top']
        bottom = block['bottom']
        left = block['left']
        right = block['right']
        for lineno in range(top, bottom):
            line = lines[lineno]
            lines[lineno] = line[:left] + ' ' * (right - left) + line[right:]
        for lineno in range(max(0, top - 1), min(len(lines), bottom + 1)):
            line = lines[lineno]
            if line[max(0, left - 3): right + 3].strip():
                raise ParseError(
                    'insufficient padding {0}-{1}\n{2}'.format(
                        left, right, line),
                    lineno)
    for lineno, line in enumerate(lines):
        if line.strip():
            raise ParseError('text outside of block\n{0}'.format(line), lineno)


def parse_tokens_to_expr(tokens):
    head = tokens.pop()
    arity = get_arity(head)
    nargs = get_nargs(arity)
    args = [parse_tokens_to_expr(tokens) for _ in xrange(nargs)]
    return Expression(head, *args)


def parse_string_to_expr(string):
    tokens = string.split()
    tokens.reverse()
    expr = parse_tokens_to_expr(tokens)
    if tokens:
        raise ValueError('trailing tokens: {0} in {1}'.format(tokens, string))
    return expr


def parse_rules(filename):
    lines = ['']
    with open(filename) as f:
        for line in f.readlines():
            lines.append(RE_COMMENT.sub('', line))
    lines.append('')
    rules = parse_lines_to_rules(lines, filename)
    check_whitespace(lines, rules)
    return rules


def parse_facts(filename):
    facts = []
    with open(filename) as f:
        for line in f.readlines():
            line = RE_COMMENT.sub('', line).strip()
            if line:
                facts.append(parse_string_to_expr(line))
    return facts
