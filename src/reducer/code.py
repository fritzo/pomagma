from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args

# ----------------------------------------------------------------------------
# Signature

_VAR = intern('VAR')
_APP = intern('APP')
_JOIN = intern('JOIN')
_FUN = intern('FUN')
_LET = intern('LET')

HOLE = intern('HOLE')
TOP = intern('TOP')
BOT = intern('BOT')
I = intern('I')
K = intern('K')
B = intern('B')
C = intern('C')
S = intern('S')


@memoize_args
def _term(*args):
    return args


def APP(lhs, rhs):
    return _term(_APP, lhs, rhs)


def JOIN(lhs, rhs):
    return _term(_JOIN, lhs, rhs)


def VAR(name):
    return _term(_VAR, intern(name))


def FUN(var, body):
    return _term(_FUN, var, body)


def LET(var, defn, body):
    return _term(_LET, var, defn, body)


def is_var(code):
    return isinstance(code, tuple) and code[0] is _VAR


def is_app(code):
    return isinstance(code, tuple) and code[0] is _APP


def is_join(code):
    return isinstance(code, tuple) and code[0] is _JOIN


def is_fun(code):
    return isinstance(code, tuple) and code[0] is _FUN


def is_let(code):
    return isinstance(code, tuple) and code[0] is _LET


@memoize_arg
def free_vars(code):
    if is_var(code):
        return set([code])
    elif is_app(code) or is_join(code):
        return free_vars(code[1]) | free_vars(code[2])
    else:
        return set()


# ----------------------------------------------------------------------------
# Parsing and seralization

def parse(string):
    assert isinstance(string, str), type(string)
    tokens = map(intern, string.split())
    tokens.reverse()
    return _parse_tokens(tokens)


def _pop_token(tokens):
    return tokens.pop()


def _parse_tokens(tokens):
    token = tokens.pop()
    try:
        parsers = _PARSERS[token]
    except KeyError:
        return token  # atom
    args = tuple(p(tokens) for p in parsers)
    return _term(token, *args)


_PARSERS = {
    _VAR: (_pop_token,),
    _APP: (_parse_tokens, _parse_tokens),
    _JOIN: (_parse_tokens, _parse_tokens),
    _FUN: (_parse_tokens, _parse_tokens),
    _LET: (_parse_tokens, _parse_tokens, _parse_tokens),
}


def serialize(code):
    tokens = []
    _serialize_tokens(code, tokens)
    return ' '.join(tokens)


def _serialize_tokens(code, tokens):
    if isinstance(code, str):
        tokens.append(code)
    elif isinstance(code, tuple):
        tokens.append(code[0])
        for arg in code[1:]:
            _serialize_tokens(arg, tokens)
