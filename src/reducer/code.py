from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
import re

# ----------------------------------------------------------------------------
# Signature

re_const = re.compile('[A-Z]+$')

_VAR = intern('VAR')
_APP = intern('APP')
_QUOTE = intern('QUOTE')
_FUN = intern('FUN')
_LET = intern('LET')

TOP = intern('TOP')
BOT = intern('BOT')
I = intern('I')
K = intern('K')
B = intern('B')
C = intern('C')
S = intern('S')
J = intern('J')

CODE = intern('CODE')
EVAL = intern('EVAL')
QAPP = intern('QAPP')
QQUOTE = intern('QQUOTE')
EQUAL = intern('EQUAL')
LESS = intern('LESS')

V = intern('V')
A = intern('A')
UNIT = intern('UNIT')
BOOL = intern('BOOL')
MAYBE = intern('MAYBE')
PROD = intern('PROD')
SUM = intern('SUM')
NUM = intern('NUM')


@memoize_args
def _term(*args):
    return args


def VAR(name):
    if re_const.match(name):
        raise ValueError('variable names cannot match [A-Z]+')
    return _term(_VAR, intern(name))


def APP(lhs, rhs):
    return _term(_APP, lhs, rhs)


def QUOTE(code):
    return _term(_QUOTE, code)


def FUN(var, body):
    return _term(_FUN, var, body)


def LET(var, defn, body):
    return _term(_LET, var, defn, body)


def is_atom(code):
    return isinstance(code, str)


def is_var(code):
    return isinstance(code, tuple) and code[0] is _VAR


def is_app(code):
    return isinstance(code, tuple) and code[0] is _APP


def is_quote(code):
    return isinstance(code, tuple) and code[0] is _QUOTE


def is_fun(code):
    return isinstance(code, tuple) and code[0] is _FUN


def is_let(code):
    return isinstance(code, tuple) and code[0] is _LET


@memoize_arg
def free_vars(code):
    if is_var(code):
        return frozenset([code])
    elif is_app(code):
        return free_vars(code[1]) | free_vars(code[2])
    elif is_quote(code):
        return free_vars(code[1])
    else:
        return frozenset()


@memoize_arg
def complexity(code):
    if isinstance(code, tuple):
        return 1 + sum(complexity(arg) for arg in code[1:])
    else:
        return 1


# ----------------------------------------------------------------------------
# Polish notation

def polish_parse(string):
    assert isinstance(string, str), type(string)
    tokens = map(intern, string.split())
    tokens.reverse()
    return _polish_parse_tokens(tokens)


def _pop_token(tokens):
    return tokens.pop()


def _polish_parse_tokens(tokens):
    token = tokens.pop()
    try:
        polish_parsers = _PARSERS[token]
    except KeyError:
        return token if re_const.match(token) else VAR(token)  # atom
    args = tuple(p(tokens) for p in polish_parsers)
    return _term(token, *args)


_PARSERS = {
    # _VAR: (_pop_token,),
    _APP: (_polish_parse_tokens, _polish_parse_tokens),
    _QUOTE: (_polish_parse_tokens,),
    _FUN: (_polish_parse_tokens, _polish_parse_tokens),
    _LET: (_polish_parse_tokens, _polish_parse_tokens, _polish_parse_tokens),
}


def polish_print(code):
    tokens = []
    _polish_print_tokens(code, tokens)
    return ' '.join(tokens)


def _polish_print_tokens(code, tokens):
    if isinstance(code, str):
        tokens.append(code)
    elif isinstance(code, tuple):
        if code[0] is not _VAR:
            tokens.append(code[0])
        for arg in code[1:]:
            _polish_print_tokens(arg, tokens)


# ----------------------------------------------------------------------------
# S-Expression notation

@memoize_arg
def to_sexpr(code):
    if isinstance(code, str):
        return code
    elif is_var(code):
        return code[1]
    head = code
    args = []
    while is_app(head):
        args.append(head[2])
        head = head[1]
    if is_var(head):
        head = head[1]
    elif is_quote(head):
        args.append(head[1])
        head = _QUOTE
    elif is_fun(head):
        args.append(head[2])
        args.append(head[1])
        head = _FUN
    elif is_let(head):
        args.append(head[3])
        args.append(head[2])
        args.append(head[1])
        head = _LET
    args = map(to_sexpr, reversed(args))
    return tuple([head] + args)


def from_sexpr(sexpr):
    if isinstance(sexpr, str):
        if re_const.match(sexpr):
            return sexpr
        else:
            return VAR(sexpr)
    head = sexpr[0]
    assert isinstance(head, str)
    if not re_const.match(head):
        head = VAR(head)
        args = sexpr[1:]
    elif head is _QUOTE:
        code = from_sexpr(sexpr[1])
        head = QUOTE(code)
        args = sexpr[2:]
    elif head is _FUN:
        var = from_sexpr(sexpr[1])
        body = from_sexpr(sexpr[2])
        head = FUN(var, body)
        args = sexpr[3:]
    elif head is _LET:
        var = from_sexpr(sexpr[1])
        defn = from_sexpr(sexpr[2])
        body = from_sexpr(sexpr[3])
        head = LET(var, defn, body)
        args = sexpr[4:]
    else:
        args = sexpr[1:]
    args = map(from_sexpr, args)
    for arg in args:
        head = APP(head, arg)
    return head


def sexpr_print_sexpr(sexpr):
    if isinstance(sexpr, str):
        return sexpr
    parts = map(sexpr_print_sexpr, sexpr)
    return '({})'.format(' '.join(parts))


@memoize_arg
def sexpr_print(code):
    sexpr = to_sexpr(code)
    return sexpr_print_sexpr(sexpr)


_LPAREN = intern('(')
_RPAREN = intern(')')


def _sexpr_parse_tokens(tokens):
    for token in tokens:
        if token is _LPAREN:
            yield tuple(_sexpr_parse_tokens(tokens))
        elif token is _RPAREN:
            raise StopIteration
        else:
            yield token


def sexpr_parse_sexpr(string):
    tokens = string.replace('(', ' ( ').replace(')', ' ) ').split()
    tokens = iter(map(intern, tokens))
    sexpr = next(_sexpr_parse_tokens(tokens))
    try:
        extra = next(tokens)
    except StopIteration:
        pass
    else:
        raise ValueError('Extra tokens at end of sexpr: {}'.format(extra))
    return sexpr


def sexpr_parse(string):
    sexpr = sexpr_parse_sexpr(string)
    code = from_sexpr(sexpr)
    return code
