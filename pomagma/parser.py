import re
import sys
from pomagma.compiler import SYMBOL_TABLE, Function, Variable, Sequent


re_bar = re.compile('---+')
re_padding = re.compile('   +')


class ParseError(Exception):
    def __init__(self, message, lineno='unknown'):
        self.message = str(message)
        self.lineno = lineno

    def __str__(self):
        return 'ParseError on line {0}: {1}'.format(self.lineno, self.message)


def find_bars(lines):
    bars = []
    for lineno, line in enumerate(lines):
        match = re_bar.search(line)
        while match:
            beg = match.start()
            end = match.end()
            bars.append((lineno, beg, end))
            match = re_bar.search(line, end)
            if match and match.start() - end < 3:
                raise ParseError('horizontal rule overlap', lineno)
    return bars


def get_sections(lines, linenos, beg, end):
    results = []
    for lineno in linenos:
        line = lines[lineno]
        section = lines[lineno][beg:end]
        stripped = section.strip()
        if re_bar.match(stripped):
            raise ParseError('vertical rule overlap', lineno)
        if stripped:
            for string in re_padding.split(stripped):
                try:
                    expr = parse_string_to_expr(string)
                except Exception as e:
                    raise ParseError('{0}\n{1}'.format(e, line), lineno)
                results.append(expr)
        else:
            break
    return lineno, results


def parse_lines_to_sequents(lines):
    lines = (lines)
    bars = find_bars(lines)
    sequents = []
    blocks = []
    for lineno, beg, end in bars:
        p, prems = get_sections(lines, xrange(lineno - 1, -1, -1), beg, end)
        c, concs = get_sections(lines, xrange(lineno + 1, len(lines)), beg, end)
        sequents.append(Sequent(prems, concs))
        blocks.append((p - 1, c, beg, end))
    print 'DEBUG', blocks
    for line0, line1, beg, end in blocks:
        for lineno in range(line0, line1):
            line = lines[lineno]
            lines[lineno] = line[:beg] + ' ' * (end - beg) + line[end:]
        for lineno in range(max(0, line0 - 1), min(len(lines), line1 + 1)):
            line = lines[lineno]
            if line[max(0, beg - 3): end + 3].strip():
                raise ParseError(
                    'insufficient padding {0}-{1}\n{2}'.format(beg, end, line),
                    lineno)
    for lineno, line in enumerate(lines):
        if line.strip():
            raise ParseError('text outside of block\n{0}'.format(line), lineno)
    return sequents


def default_parser(token):
    if re.match('[A-Z_]', token[-1]):
        return 0, lambda: Function(token)
    else:
        return 0, lambda: Variable(token)

def parse_tokens_to_expr(tokens):
    head = tokens.pop()
    arity, parser = SYMBOL_TABLE.get(head, default_parser(head))
    args = [parse_tokens_to_expr(tokens) for _ in xrange(arity)]
    return parser(*args)


def tokenize(string):
    tokens = string.split()
    tokens.reverse()
    return tokens


def parse_string_to_expr(string):
    tokens = tokenize(string)
    expr = parse_tokens_to_expr(tokens)
    if tokens:
        raise ValueError('trailing tokens: {0} in {1}'.format(tokens, string))
    return expr


def parse(filename):
    #sys.stderr.write('# parsing {}\n'.format(filename))
    with open(filename) as f:
        return parse_lines_to_sequents([''] + list(f.readlines()) + [''])
