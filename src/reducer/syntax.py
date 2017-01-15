import re
from collections import defaultdict

from pomagma.compiler.util import (MEMOIZED_CACHES, memoize_arg, memoize_args,
                                   unique_result)
from pomagma.reducer.util import UnreachableError


# ----------------------------------------------------------------------------
# Signature

class CodeTuple(tuple):
    def __str__(self):
        return '{}({})'.format(self[0], ', '.join(str(a) for a in self[1:]))


_CODES = {}


def _code(*args):
    # This can be used for pretty printing during debugging,
    # but is disabled to avoid churn in term ordering.
    # args = CodeTuple(args)

    # Slow version:
    # value = args if len(args) > 1 else args[0]
    # return _CODES.setdefault(args, value)

    # Fast version (works because of make_keyword(-) below):
    return _CODES.setdefault(args, args)


MEMOIZED_CACHES[_code] = _CODES


def isa_code(arg):
    try:
        return _CODES[arg] is arg
    except KeyError:
        return False


re_keyword = re.compile('[A-Z]+$')
re_rank = re.compile(r'\d+$')
_keywords = {}  # : name -> arity
_builders = {}  # : name -> constructor


def make_keyword(name, arity=0):
    assert re_keyword.match(name)
    assert name not in _keywords
    assert arity in [0, 1, 2]
    name = intern(name)
    _keywords[name] = arity
    _CODES[name] = name
    return name


def builder(fun):
    name = intern(fun.__name__)
    assert name in _keywords, name
    assert _keywords[name] > 0, (name, _keywords[name])
    assert name not in _builders, name
    _builders[name] = fun
    return fun


_IVAR = make_keyword('IVAR', 1)  # de Bruijn variable.
_NVAR = make_keyword('NVAR', 1)  # Nominal variable.
_APP = make_keyword('APP', 2)
_JOIN = make_keyword('JOIN', 2)
_QUOTE = make_keyword('QUOTE', 1)
_ABS = make_keyword('ABS', 1)  # de Bruijn abstraction.
_FUN = make_keyword('FUN', 2)  # Nominal abstraction.
_REC = make_keyword('REC', 1)  # de Bruijn recursion.
_LESS = make_keyword('LESS', 2)
_NLESS = make_keyword('NLESS', 2)
_EQUAL = make_keyword('EQUAL', 2)

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
QEQUAL = make_keyword('QEQUAL')
QLESS = make_keyword('QLESS')

V = make_keyword('V')
A = make_keyword('A')
UNIT = make_keyword('UNIT')
BOOL = make_keyword('BOOL')
MAYBE = make_keyword('MAYBE')
PROD = make_keyword('PROD')
SUM = make_keyword('SUM')
NUM = make_keyword('NUM')


@builder
def NVAR(name):
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    return _code(_NVAR, intern(name))


@builder
def IVAR(rank):
    if not (isinstance(rank, int) and rank >= 0):
        raise ValueError(
            'Variable index must be a natural number {}'.format(rank))
    return _code(_IVAR, rank)


IVAR_0 = IVAR(0)


@builder
def APP(lhs, rhs):
    return _code(_APP, lhs, rhs)


@builder
def JOIN(lhs, rhs):
    return _code(_JOIN, lhs, rhs)


@builder
def QUOTE(code):
    # TODO assert all(not isa_ivar(v) for v in free_vars(code))
    return _code(_QUOTE, code)


@builder
def ABS(body):
    assert IVAR_0 not in quoted_vars(body)
    return _code(_ABS, body)


@builder
def FUN(var, body):
    assert isa_nvar(var), var
    assert var not in quoted_vars(body), (var, body)
    return _code(_FUN, var, body)


@builder
def REC(body):
    assert IVAR_0 not in quoted_vars(body)
    return _code(_REC, body)


@builder
def LESS(lhs, rhs):
    return _code(_LESS, lhs, rhs)


@builder
def NLESS(lhs, rhs):
    return _code(_NLESS, lhs, rhs)


@builder
def EQUAL(lhs, rhs):
    return _code(_EQUAL, lhs, rhs)


def isa_atom(code):
    assert isa_code(code), code
    return isinstance(code, str)


def isa_nvar(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _NVAR


def isa_ivar(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _IVAR


def isa_app(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _APP


def isa_join(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _JOIN


def isa_quote(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _QUOTE


def isa_abs(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _ABS


def isa_fun(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _FUN


def isa_rec(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _REC


def isa_equal(code):
    assert isa_code(code), code
    return isinstance(code, tuple) and code[0] is _EQUAL


# ----------------------------------------------------------------------------
# Transforms

class Transform(object):
    """Recursive transform of code."""

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @memoize_args
    def __call__(self, code):
        if not isa_code(code):
            raise TypeError(code)
        elif isa_atom(code):
            return getattr(self, code)
        elif isa_nvar(code):
            return self.NVAR(code[1])
        elif isa_ivar(code):
            return self.IVAR(code[1])
        else:
            args = [self(arg) for arg in code[1:]]
            return getattr(self, code[0])(*args)

    NVAR = staticmethod(NVAR)
    IVAR = staticmethod(IVAR)
    APP = staticmethod(APP)
    JOIN = staticmethod(JOIN)
    QUOTE = staticmethod(QUOTE)
    ABS = staticmethod(ABS)
    FUN = staticmethod(FUN)
    REC = staticmethod(REC)

    @classmethod
    def init_atoms(cls):
        for name, arity in _keywords.iteritems():
            if arity == 0:
                setattr(cls, name, name)


Transform.init_atoms()
identity = Transform()


# ----------------------------------------------------------------------------
# Variables

def anonymize(code, var, transform=identity):
    """Convert a nominal variable to a de Bruijn variable."""
    return _anonymize(code, var, 0, transform)


@memoize_args
def _anonymize(code, var, rank, transform):
    """Convert a nominal variable to a de Bruijn variable."""
    if code is var:
        return transform.IVAR(rank)
    elif isa_atom(code) or isa_nvar(code):
        return transform(code)
    elif isa_ivar(code):
        if code[1] < rank:
            return transform.IVAR(code[1])
        else:
            return transform.IVAR(code[1] + 1)
    elif isa_abs(code):
        body = _anonymize(code[1], var, rank + 1, transform)
        return transform.ABS(body)
    elif isa_rec(code):
        body = _anonymize(code[1], var, rank + 1, transform)
        return transform.REC(body)
    elif isa_app(code):
        lhs = _anonymize(code[1], var, rank, transform)
        rhs = _anonymize(code[2], var, rank, transform)
        return transform.APP(lhs, rhs)
    elif isa_join(code):
        lhs = _anonymize(code[1], var, rank, transform)
        rhs = _anonymize(code[2], var, rank, transform)
        return transform.JOIN(lhs, rhs)
    elif isa_quote(code):
        body = _anonymize(code[1], var, rank, transform)
        return transform.QUOTE(body)
    else:
        raise ValueError(code)
    raise UnreachableError(code)


def decrement_var(var):
    """Decrement rank of an IVAR or leave an NVAR untouched."""
    if isa_nvar(var):
        return var
    elif isa_ivar(var):
        assert var[1] > 0, var
        return IVAR(var[1] - 1)
    else:
        raise ValueError(var)
    raise UnreachableError(var)


@memoize_arg
@unique_result
def free_vars(code):
    """Returns set of free variables, possibly quoted."""
    assert isa_code(code), code
    if isa_atom(code):
        return frozenset()
    elif isa_nvar(code) or isa_ivar(code):
        return frozenset([code])
    elif isa_app(code) or isa_join(code):
        return free_vars(code[1]) | free_vars(code[2])
    elif isa_quote(code):
        return free_vars(code[1])
    elif isa_abs(code) or isa_rec(code):
        return frozenset(
            decrement_var(v)
            for v in free_vars(code[1])
            if v is not IVAR_0
        )
    elif isa_fun(code):
        assert isa_nvar(code[1])
        return free_vars(code[2]) - frozenset([code[1]])
    else:
        raise ValueError(code)
    raise UnreachableError(code)


@memoize_arg
@unique_result
def quoted_vars(code):
    """Returns set of free quoted variables."""
    assert isa_code(code), code
    if isa_atom(code) or isa_nvar(code) or isa_ivar(code):
        return frozenset()
    elif isa_quote(code):
        return free_vars(code[1])
    elif isa_app(code) or isa_join(code):
        return quoted_vars(code[1]) | quoted_vars(code[2])
    elif isa_abs(code) or isa_rec(code):
        return frozenset(
            decrement_var(v)
            for v in quoted_vars(code[1])
            if v is not IVAR_0
        )
    elif isa_fun(code):
        return quoted_vars(code[2])
    else:
        raise ValueError(code)
    raise UnreachableError(code)


@memoize_arg
def is_closed(code):
    """A code is closed if all de Bruijn variables are bound."""
    return not any(isa_ivar(v) for v in free_vars(code))


@memoize_arg
def is_defined(code):
    """A code is defined if all nominal variables have been substituted."""
    return not any(isa_nvar(v) for v in free_vars(code))


# ----------------------------------------------------------------------------
# Complexity

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

    Theorem: Modulo alpha conversion and excluding JOIN-terms,
      there are finitely many codes with any fixed complexity.
    Theorem: There are finitely many JOIN-free closed de Bruijn terms
      at any given complexity.

    """
    assert isa_code(code), code
    if isa_atom(code):
        return ATOM_COMPLEXITY[code]
    elif isa_nvar(code) or isa_ivar(code):
        return 1
    elif isa_join(code):
        return max(complexity(code[1]), complexity(code[2]))
    elif isinstance(code, tuple):
        return 1 + max(complexity(arg) for arg in code[1:])
    else:
        raise ValueError(code)
    raise UnreachableError(code)


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
    _REC: (_polish_parse_tokens,),
    _LESS: (_polish_parse_tokens, _polish_parse_tokens),
    _NLESS: (_polish_parse_tokens, _polish_parse_tokens),
    _EQUAL: (_polish_parse_tokens, _polish_parse_tokens),
}


def polish_print(code):
    assert isa_code(code), code
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
    assert isa_code(code), code
    if isinstance(code, str):
        return code
    elif isa_nvar(code) or isa_ivar(code):
        return code[1]
    head = code
    args = []
    while isa_app(head):
        args.append(to_sexpr(head[2]))
        head = head[1]
    if isa_nvar(head) or isa_ivar(head):
        head = head[1]
    elif head[0] in _builders:
        for arg in head[-1:0:-1]:
            args.append(to_sexpr(arg))
        head = head[0]
    args.append(head)
    args.reverse()
    return tuple(args)


def from_sexpr(sexpr, signature={}):
    """Converts from a python S-expression to a python code."""
    assert isinstance(signature, dict), type(signature)

    # Handle atoms.
    if isinstance(sexpr, str):
        if sexpr in _keywords:
            return signature.get(sexpr, sexpr)
        else:
            if re_keyword.match(sexpr):
                raise ValueError('Unrecognized keyword: {}'.format(sexpr))
            return NVAR(sexpr)
    if isinstance(sexpr, int):
        return IVAR(sexpr)

    # Handle tuples.
    head = sexpr[0]
    assert isinstance(head, (str, int))
    if head in _keywords:
        arity = _keywords[head]
        if arity:
            if len(sexpr) < 1 + arity:
                raise ValueError('Too few args to {}: {}'.format(head, sexpr))
            builder = signature.get(head, _builders[head])
            head = builder(*(
                from_sexpr(sexpr[1 + i], signature)
                for i in xrange(arity)
            ))
        else:
            head = signature.get(head, head)
        args = sexpr[1 + arity:]
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
    assert isa_code(code), code
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
