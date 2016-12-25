from collections import defaultdict
from pomagma.compiler.util import MEMOIZED_CACHES
from pomagma.compiler.util import memoize_arg
import re


# ----------------------------------------------------------------------------
# Signature

_CODES = {}


def _code(*args):
    # Slow version:
    # value = args if len(args) > 1 else args[0]
    # return _CODES.setdefault(args, value)

    # Fast version (works because of make_keyword(-) below):
    return _CODES.setdefault(args, args)


MEMOIZED_CACHES[_code] = _CODES


def is_code(arg):
    try:
        return _CODES[arg] is arg
    except KeyError:
        return False


re_keyword = re.compile('[A-Z]+$')
re_rank = re.compile(r'\d+$')
_keywords = set()


def make_keyword(name):
    assert re_keyword.match(name)
    assert name not in _keywords
    name = intern(name)
    _keywords.add(name)
    _CODES[name] = name
    return name


_IVAR = make_keyword('IVAR')  # de Bruijn variable.
_NVAR = make_keyword('NVAR')  # Nominal variable.
_APP = make_keyword('APP')
_JOIN = make_keyword('JOIN')
_QUOTE = make_keyword('QUOTE')
_ABS = make_keyword('ABS')  # de Bruijn abstraction.
_FUN = make_keyword('FUN')  # Nominal abstraction.
_LET = make_keyword('LET')

TOP = make_keyword('TOP')
BOT = make_keyword('BOT')
I = make_keyword('I')
K = make_keyword('K')
B = make_keyword('B')
C = make_keyword('C')
S = make_keyword('S')

CODE = make_keyword('CODE')
EVAL = make_keyword('EVAL')
QAPP = make_keyword('QAPP')
QQUOTE = make_keyword('QQUOTE')
EQUAL = make_keyword('EQUAL')
LESS = make_keyword('LESS')

V = make_keyword('V')
A = make_keyword('A')
UNIT = make_keyword('UNIT')
BOOL = make_keyword('BOOL')
MAYBE = make_keyword('MAYBE')
PROD = make_keyword('PROD')
SUM = make_keyword('SUM')
NUM = make_keyword('NUM')


def NVAR(name):
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    return _code(_NVAR, intern(name))


def IVAR(rank):
    if not isinstance(rank, int) and rank >= 0:
        raise ValueError(
            'Variable index must be a natural number {}'.format(rank))
    return _code(_IVAR, rank)


def APP(lhs, rhs):
    return _code(_APP, lhs, rhs)


def JOIN(lhs, rhs):
    return _code(_JOIN, lhs, rhs)


def QUOTE(code):
    return _code(_QUOTE, code)


def ABS(body):
    return _code(_ABS, body)


def FUN(var, body):
    return _code(_FUN, var, body)


def LET(var, defn, body):
    return _code(_LET, var, defn, body)


def is_atom(code):
    assert is_code(code), code
    return isinstance(code, str)


def is_nvar(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _NVAR


def is_ivar(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _IVAR


def is_app(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _APP


def is_join(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _JOIN


def is_quote(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _QUOTE


def is_abs(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _ABS


def is_fun(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _FUN


def is_let(code):
    assert is_code(code), code
    return isinstance(code, tuple) and code[0] is _LET


@memoize_arg
def free_vars(code):
    """Returns set of free nominal variables."""
    assert is_code(code), code
    if is_nvar(code):
        return frozenset([code])
    elif is_app(code) or is_join(code):
        return free_vars(code[1]) | free_vars(code[2])
    elif is_quote(code):
        return free_vars(code[1])  # FIXME
    elif is_abs(code):
        return free_vars(code[1])
    elif is_fun(code):
        assert is_nvar(code[1])
        return free_vars(code[2]) - frozenset([code[1]])
    elif is_let(code):
        assert is_nvar(code[1])
        return free_vars(code[3]) - frozenset([code[1]]) | free_vars(code[2])
    else:
        return frozenset()


# Term complexity is roughly the depth of a term, with special cases for atoms,
# variables, and joins. The complexity of a join is the max complexity of each
# part of the join.
ATOM_COMPLEXITY = defaultdict(lambda: 10, {
    BOT: 0,
    TOP: 0,
    I: 2,  # \x.x
    K: 3,  # \x,y. x
    B: 6,  # \x,y,z. x (y z)
    C: 6,  # \x,y,z. x z y
    S: 6,  # \x,y,z. x z (y z)
    # V: TODO(),
    # A: TODO(),
})


@memoize_arg
def complexity(code):
    """Complexity norm on code.

    Theorem: Modulo alpha conversion,
      there are finitely many codes with any fixed complexity.
    Theorem: There are finitely many closed de Bruijn terms at any given
      complexity.

    """
    assert is_code(code), code
    if is_atom(code):
        return ATOM_COMPLEXITY[code]
    elif is_nvar(code) or is_ivar(code):
        return 1
    elif is_join(code):
        return max(complexity(code[1]), complexity(code[2]))
    elif isinstance(code, tuple):
        return 1 + max(complexity(arg) for arg in code[1:])
    else:
        raise ValueError(code)


# ----------------------------------------------------------------------------
# Polish notation

def polish_parse(string, signature={}):
    """Parse a string from polish notation to a code.

    Args:
      string: a string in polish notation.
      signature: an optional dict of overrides, mapping keyword to builder.

    Returns:
      a code.
    """
    assert isinstance(string, str), type(string)
    assert isinstance(signature, dict), type(signature)
    tokens = map(intern, string.split())
    tokens.reverse()
    return _polish_parse_tokens(tokens, signature)


def _pop_token(tokens, signature):
    return tokens.pop()


def _pop_int(tokens, signature):
    return int(tokens.pop())


def _polish_parse_tokens(tokens, signature):
    token = tokens.pop()
    try:
        polish_parsers = _PARSERS[token]
    except KeyError:
        if re_keyword.match(token):
            return signature.get(token, token)
        elif re_rank.match(token):
            return IVAR(int(token))
        else:
            return NVAR(token)
    args = tuple(p(tokens, signature) for p in polish_parsers)
    try:
        fun = signature[token]
    except KeyError:
        return _code(token, *args)
    return fun(*args)


_PARSERS = {
    _APP: (_polish_parse_tokens, _polish_parse_tokens),
    _JOIN: (_polish_parse_tokens, _polish_parse_tokens),
    _QUOTE: (_polish_parse_tokens,),
    _ABS: (_polish_parse_tokens,),
    _FUN: (_polish_parse_tokens, _polish_parse_tokens),
    _LET: (_polish_parse_tokens, _polish_parse_tokens, _polish_parse_tokens),
}


def polish_print(code):
    assert is_code(code), code
    tokens = []
    _polish_print_tokens(code, tokens)
    return ' '.join(tokens)


def _polish_print_tokens(code, tokens):
    if isinstance(code, str):
        tokens.append(code)
    elif isinstance(code, tuple):
        if code[0] is _NVAR:
            tokens.append(code[1])
            pos = 2
        elif code[0] is _IVAR:
            tokens.append(str(code[1]))
            pos = 2
        else:
            tokens.append(code[0])
            pos = 1
        for arg in code[pos:]:
            _polish_print_tokens(arg, tokens)
    elif isinstance(code, int):
        tokens.append(str(code))
    else:
        raise ValueError(code)


# ----------------------------------------------------------------------------
# S-Expression notation

@memoize_arg
def to_sexpr(code):
    """Converts from a python code to a python S-expression."""
    assert is_code(code), code
    if isinstance(code, str):
        return code
    elif is_nvar(code) or is_ivar(code):
        return code[1]
    head = code
    args = []
    while is_app(head):
        args.append(to_sexpr(head[2]))
        head = head[1]
    if is_nvar(head) or is_ivar(head):
        head = head[1]
    elif is_join(head):
        args.append(to_sexpr(head[2]))
        args.append(to_sexpr(head[1]))
        head = _JOIN
    elif is_quote(head):
        args.append(to_sexpr(head[1]))
        head = _QUOTE
    elif is_abs(head):
        args.append(to_sexpr(head[1]))
        head = _ABS
    elif is_fun(head):
        args.append(to_sexpr(head[2]))
        args.append(to_sexpr(head[1]))
        head = _FUN
    elif is_let(head):
        args.append(to_sexpr(head[3]))
        args.append(to_sexpr(head[2]))
        args.append(to_sexpr(head[1]))
        head = _LET
    args.append(head)
    args.reverse()
    return tuple(args)


def from_sexpr(sexpr, signature={}):
    """Converts from a python S-expression to a python code."""
    assert isinstance(signature, dict), type(signature)
    if isinstance(sexpr, str):
        if sexpr in _keywords:
            return signature.get(sexpr, sexpr)
        else:
            if re_keyword.match(sexpr):
                raise ValueError('Unrecognized keyword: {}'.format(sexpr))
            return NVAR(sexpr)
    if isinstance(sexpr, int):
        return IVAR(sexpr)
    head = sexpr[0]
    assert isinstance(head, (str, int))
    if head in _keywords:
        if head is _JOIN:
            lhs = from_sexpr(sexpr[1], signature)
            rhs = from_sexpr(sexpr[2], signature)
            head = signature.get('JOIN', JOIN)(lhs, rhs)
            args = sexpr[3:]
        elif head is _QUOTE:
            code = from_sexpr(sexpr[1], signature)
            head = signature.get('QUOTE', QUOTE)(code)
            args = sexpr[2:]
        elif head is _ABS:
            body = from_sexpr(sexpr[1], signature)
            head = signature.get('ABS', ABS)(body)
            args = sexpr[2:]
        elif head is _FUN:
            var = from_sexpr(sexpr[1], signature)
            body = from_sexpr(sexpr[2], signature)
            head = signature.get('FUN', FUN)(var, body)
            args = sexpr[3:]
        elif head is _LET:
            var = from_sexpr(sexpr[1], signature)
            defn = from_sexpr(sexpr[2], signature)
            body = from_sexpr(sexpr[3], signature)
            head = signature.get('LET', LET)(var, defn, body)
            args = sexpr[4:]
        else:
            head = signature.get(head, head)
            args = sexpr[1:]
    elif isinstance(head, int):
        head = IVAR(head)
        args = sexpr[1:]
    else:
        head = NVAR(head)
        args = sexpr[1:]
    for arg in args:
        arg = from_sexpr(arg, signature)
        head = signature.get('APP', APP)(head, arg)
    return head


def sexpr_print_sexpr(sexpr):
    """Prints a python S-expression as a string S-expression."""
    if isinstance(sexpr, str):
        return sexpr
    if isinstance(sexpr, int):
        return str(sexpr)
    parts = map(sexpr_print_sexpr, sexpr)
    return '({})'.format(' '.join(parts))


@memoize_arg
def sexpr_print(code):
    """Prints a python code as a string S-expression."""
    assert is_code(code), code
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
        elif re_rank.match(token):
            yield int(token)
        else:
            yield token


def sexpr_parse_sexpr(string):
    """Parses a string S-expression to a python S-expression."""
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


def sexpr_parse(string, signature={}):
    """Parse a string from S-expressoin notation to a code.

    Args:
      string: a string in S-expression notation.
      signature: an optional dict of overrides, mapping keyword to builder.

    Returns:
      a code.
    """
    assert isinstance(string, str), type(string)
    assert isinstance(signature, dict), type(signature)
    sexpr = sexpr_parse_sexpr(string)
    code = from_sexpr(sexpr, signature)
    return code
