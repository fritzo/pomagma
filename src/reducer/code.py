from collections import defaultdict
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
import re

# ----------------------------------------------------------------------------
# Signature

re_keyword = re.compile('[A-Z]+$')
_keywords = set()


def make_keyword(name):
    assert re_keyword.match(name)
    assert name not in _keywords
    name = intern(name)
    _keywords.add(name)
    return name


_VAR = make_keyword('VAR')  # Nonimal variable.
_IVAR = make_keyword('IVAR')  # de Bruijn variable.
_APP = make_keyword('APP')
_QUOTE = make_keyword('QUOTE')
_FUN = make_keyword('FUN')
_LET = make_keyword('LET')
_ABIND = make_keyword('ABIND')
_RVAR = make_keyword('RVAR')
_SVAR = make_keyword('SVAR')

TOP = make_keyword('TOP')
BOT = make_keyword('BOT')
I = make_keyword('I')
K = make_keyword('K')
B = make_keyword('B')
C = make_keyword('C')
S = make_keyword('S')
J = make_keyword('J')

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


@memoize_args
def _term(*args):
    return args


def VAR(name):
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    return _term(_VAR, intern(name))


def IVAR(rank):
    if not isinstance(rank, int) and rank >= 0:
        raise ValueError(
            'Variable index must be a natural number {}'.format(rank))
    return _term(_IVAR, rank)


def APP(lhs, rhs):
    return _term(_APP, lhs, rhs)


def QUOTE(code):
    return _term(_QUOTE, code)


def FUN(var, body):
    return _term(_FUN, var, body)


def LET(var, defn, body):
    return _term(_LET, var, defn, body)


def ABIND(name, body):
    return _term(_ABIND, intern(name), body)


def RVAR(name):
    return _term(_RVAR, intern(name))


def SVAR(name):
    return _term(_SVAR, intern(name))


def is_atom(code):
    return isinstance(code, str)


def is_var(code):
    return isinstance(code, tuple) and code[0] is _VAR


def is_ivar(term):
    return isinstance(term, tuple) and term[0] is _IVAR


def is_app(code):
    return isinstance(code, tuple) and code[0] is _APP


def is_quote(code):
    return isinstance(code, tuple) and code[0] is _QUOTE


def is_fun(code):
    return isinstance(code, tuple) and code[0] is _FUN


def is_let(code):
    return isinstance(code, tuple) and code[0] is _LET


def is_abind(code):
    return isinstance(code, tuple) and code[0] is _ABIND


def is_rvar(code):
    return isinstance(code, tuple) and code[0] is _RVAR


def is_svar(code):
    return isinstance(code, tuple) and code[0] is _SVAR


@memoize_arg
def free_vars(code):
    if is_var(code):
        return frozenset([code])
    elif is_app(code):
        return free_vars(code[1]) | free_vars(code[2])
    elif is_quote(code):
        return free_vars(code[1])
    elif is_fun(code):
        assert is_var(code[1])
        return free_vars(code[2]) - frozenset([code[1]])
    elif is_fun(code):
        assert is_var(code[1])
        return free_vars(code[3]) - frozenset([code[1]]) | free_vars(code[2])
    elif is_abind(code):
        return free_vars(code[2])
    else:
        return frozenset()


# Atom complexity is the count of number of variable occurrences, with either
# positive or negative valence. The complexity of a join is the max of 1 and
# the max complexity of each part of the join.
ATOM_COMPLEXITY = defaultdict(lambda: 99, {
    BOT: 1,
    TOP: 1,
    I: 2,  # \x.x
    K: 3,  # \x,y. x
    B: 6,  # \x,y,z. x (y z)
    C: 6,  # \x,y,z. x z y
    S: 7,  # \x,y,z. x z (y z)
    J: 3,  # (\x,y. x) | (\x,y. y)
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
    if is_atom(code):
        return ATOM_COMPLEXITY[code]
    elif is_var(code) or is_ivar(code) or is_rvar(code) or is_svar(code):
        return 1
    elif isinstance(code, tuple):
        if len(code) > 2:
            return sum(complexity(arg) for arg in code[1:])
        else:
            assert len(code) == 2, code
            return 1 + complexity(code[1])
    else:
        raise ValueError(code)


# ----------------------------------------------------------------------------
# Polish notation

def polish_parse(string):
    assert isinstance(string, str), type(string)
    tokens = map(intern, string.split())
    tokens.reverse()
    return _polish_parse_tokens(tokens)


def _pop_token(tokens):
    return tokens.pop()


def _pop_int(tokens):
    return int(tokens.pop())


def _polish_parse_tokens(tokens):
    token = tokens.pop()
    try:
        polish_parsers = _PARSERS[token]
    except KeyError:
        return token if re_keyword.match(token) else VAR(token)  # atom
    args = tuple(p(tokens) for p in polish_parsers)
    return _term(token, *args)


_PARSERS = {
    _APP: (_polish_parse_tokens, _polish_parse_tokens),
    _QUOTE: (_polish_parse_tokens,),
    _FUN: (_polish_parse_tokens, _polish_parse_tokens),
    _LET: (_polish_parse_tokens, _polish_parse_tokens, _polish_parse_tokens),
    _ABIND: (_pop_token, _polish_parse_tokens),
    _IVAR: (_pop_int,),
    _RVAR: (_pop_token,),
    _SVAR: (_pop_token,),
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
    elif isinstance(code, int):
        tokens.append(str(code))
    else:
        raise ValueError(code)


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
    elif is_abind(head):
        args.append(head[2])
        args.append(head[1])
        head = _ABIND
    elif is_ivar(head):
        args.append(str(head[1]))
        head = _IVAR
    elif is_rvar(head):
        args.append(head[1])
        head = _RVAR
    elif is_svar(head):
        args.append(head[1])
        head = _SVAR
    args = map(to_sexpr, reversed(args))
    return tuple([head] + args)


def from_sexpr(sexpr):
    if isinstance(sexpr, str):
        if sexpr in _keywords:
            return sexpr
        else:
            if re_keyword.match(sexpr):
                raise ValueError('Unrecognized keyword: {}'.format(sexpr))
            return VAR(sexpr)
    head = sexpr[0]
    assert isinstance(head, str)
    if head in _keywords:
        if head is _QUOTE:
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
        elif head is _ABIND:
            body = from_sexpr(sexpr[2])
            head = ABIND(sexpr[1], body)
            args = sexpr[3:]
        elif head is _IVAR:
            head = IVAR(int(sexpr[1]))
            args = sexpr[2:]
        elif head is _RVAR:
            head = RVAR(sexpr[1])
            args = sexpr[2:]
        elif head is _SVAR:
            head = SVAR(sexpr[1])
            args = sexpr[2:]
        else:
            args = sexpr[1:]
    else:
        if re_keyword.match(head):
            raise ValueError('Unrecognized keyword: {}'.format(head))
        head = VAR(head)
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
