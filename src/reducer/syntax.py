import re
from collections import defaultdict

from pomagma.compiler.util import memoize_arg, memoize_args, unique_result
from pomagma.reducer.util import UnreachableError


# ----------------------------------------------------------------------------
# Signature

class Term(tuple):
    def __repr__(self):
        if len(self) == 1:
            return self[0]
        return '{}({})'.format(self[0], ', '.join(repr(a) for a in self[1:]))

    def __str__(self):
        if len(self) == 1:
            return self[0]
        return '{}({})'.format(self[0], ', '.join(str(a) for a in self[1:]))

    def __call__(*args):
        # This syntax will be defined later:
        # return pomagma.reducer.sugar.app(*args)
        raise NotImplementedError('import pomagma.reduce.sugar')

    def __or__(lhs, rhs):
        # This syntax will be defined later:
        # return pomagma.reducer.sugar.join_(lhs, rhs)
        raise NotImplementedError('import pomagma.reduce.sugar')

    @staticmethod
    @memoize_args
    def make(*args):
        return Term(args)


re_keyword = re.compile('[A-Z]+$')
re_rank = re.compile(r'\d+$')
_keywords = {}  # : name -> arity
_builders = {}  # : name -> constructor
_atoms = {}  # name -> term


def make_keyword(name, arity):
    assert re_keyword.match(name)
    assert name not in _keywords
    assert arity in [0, 1, 2]
    name = intern(name)
    _keywords[name] = arity
    return name


def make_atom(name):
    assert name not in _atoms
    name = make_keyword(name, arity=0)
    term = Term.make(name)
    _atoms[name] = term
    return term


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
_LESS = make_keyword('LESS', 2)
_NLESS = make_keyword('NLESS', 2)
_EQUAL = make_keyword('EQUAL', 2)

TOP = make_atom('TOP')
BOT = make_atom('BOT')
I = make_atom('I')
K = make_atom('K')
B = make_atom('B')
C = make_atom('C')
S = make_atom('S')
Y = make_atom('Y')

CODE = make_atom('CODE')
EVAL = make_atom('EVAL')
QAPP = make_atom('QAPP')
QQUOTE = make_atom('QQUOTE')
QEQUAL = make_atom('QEQUAL')
QLESS = make_atom('QLESS')

V = make_atom('V')
A = make_atom('A')
UNIT = make_atom('UNIT')
BOOL = make_atom('BOOL')
MAYBE = make_atom('MAYBE')
PROD = make_atom('PROD')
SUM = make_atom('SUM')
NUM = make_atom('NUM')


@builder
def NVAR(name):
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    return Term.make(_NVAR, intern(name))


@builder
def IVAR(rank):
    if not (isinstance(rank, int) and rank >= 0):
        raise ValueError(
            'Variable index must be a natural number {}'.format(rank))
    return Term.make(_IVAR, rank)


IVAR_0 = IVAR(0)


@builder
def APP(lhs, rhs):
    return Term.make(_APP, lhs, rhs)


@builder
def JOIN(lhs, rhs):
    return Term.make(_JOIN, lhs, rhs)


@builder
def QUOTE(term):
    # TODO assert all(not isa_ivar(v) for v in free_vars(term))
    return Term.make(_QUOTE, term)


@builder
def ABS(body):
    assert IVAR_0 not in quoted_vars(body)
    return Term.make(_ABS, body)


@builder
def FUN(var, body):
    assert isa_nvar(var), var
    assert var not in quoted_vars(body), (var, body)
    return Term.make(_FUN, var, body)


@builder
def LESS(lhs, rhs):
    return Term.make(_LESS, lhs, rhs)


@builder
def NLESS(lhs, rhs):
    return Term.make(_NLESS, lhs, rhs)


@builder
def EQUAL(lhs, rhs):
    return Term.make(_EQUAL, lhs, rhs)


def isa_atom(term):
    assert isinstance(term, Term), term
    return len(term) == 1


def isa_nvar(term):
    assert isinstance(term, Term), term
    return term[0] is _NVAR


def isa_ivar(term):
    assert isinstance(term, Term), term
    return term[0] is _IVAR


def isa_app(term):
    assert isinstance(term, Term), term
    return term[0] is _APP


def isa_join(term):
    assert isinstance(term, Term), term
    return term[0] is _JOIN


def isa_quote(term):
    assert isinstance(term, Term), term
    return term[0] is _QUOTE


def isa_abs(term):
    assert isinstance(term, Term), term
    return term[0] is _ABS


def isa_fun(term):
    assert isinstance(term, Term), term
    return term[0] is _FUN


def isa_equal(term):
    assert isinstance(term, Term), term
    return term[0] is _EQUAL


# ----------------------------------------------------------------------------
# Transforms

class Transform(object):
    """Recursive transform of term."""

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @memoize_args
    def __call__(self, term):
        if not isinstance(term, Term):
            raise TypeError(term)
        elif isa_atom(term):
            return getattr(self, term[0])
        elif isa_nvar(term):
            return self.NVAR(term[1])
        elif isa_ivar(term):
            return self.IVAR(term[1])
        else:
            args = [self(arg) for arg in term[1:]]
            return getattr(self, term[0])(*args)

    @classmethod
    def init_class(cls):
        for name, term in _atoms.iteritems():
            setattr(cls, name, term)
        for name, builder in _builders.iteritems():
            setattr(cls, name, staticmethod(builder))


Transform.init_class()
identity = Transform()


# ----------------------------------------------------------------------------
# Variables

def anonymize(term, var, transform=identity):
    """Convert a nominal variable to a de Bruijn variable."""
    return _anonymize(term, var, 0, transform)


@memoize_args
def _anonymize(term, var, rank, transform):
    """Convert a nominal variable to a de Bruijn variable."""
    if term is var:
        return transform.IVAR(rank)
    elif isa_atom(term) or isa_nvar(term):
        return transform(term)
    elif isa_ivar(term):
        if term[1] < rank:
            return transform.IVAR(term[1])
        else:
            return transform.IVAR(term[1] + 1)
    elif isa_abs(term):
        body = _anonymize(term[1], var, rank + 1, transform)
        return transform.ABS(body)
    elif isa_app(term):
        lhs = _anonymize(term[1], var, rank, transform)
        rhs = _anonymize(term[2], var, rank, transform)
        return transform.APP(lhs, rhs)
    elif isa_join(term):
        lhs = _anonymize(term[1], var, rank, transform)
        rhs = _anonymize(term[2], var, rank, transform)
        return transform.JOIN(lhs, rhs)
    elif isa_quote(term):
        body = _anonymize(term[1], var, rank, transform)
        return transform.QUOTE(body)
    else:
        raise ValueError(term)
    raise UnreachableError(term)


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
def free_vars(term):
    """Returns set of free variables, possibly quoted."""
    assert isinstance(term, Term), term
    if isa_atom(term):
        return frozenset()
    elif isa_nvar(term) or isa_ivar(term):
        return frozenset([term])
    elif isa_app(term) or isa_join(term):
        return free_vars(term[1]) | free_vars(term[2])
    elif isa_quote(term):
        return free_vars(term[1])
    elif isa_abs(term):
        return frozenset(
            decrement_var(v)
            for v in free_vars(term[1])
            if v is not IVAR_0
        )
    elif isa_fun(term):
        assert isa_nvar(term[1])
        return free_vars(term[2]) - frozenset([term[1]])
    else:
        raise ValueError(term)
    raise UnreachableError(term)


@memoize_arg
@unique_result
def quoted_vars(term):
    """Returns set of free quoted variables."""
    assert isinstance(term, Term), term
    if isa_atom(term) or isa_nvar(term) or isa_ivar(term):
        return frozenset()
    elif isa_quote(term):
        return free_vars(term[1])
    elif isa_app(term) or isa_join(term):
        return quoted_vars(term[1]) | quoted_vars(term[2])
    elif isa_abs(term):
        return frozenset(
            decrement_var(v)
            for v in quoted_vars(term[1])
            if v is not IVAR_0
        )
    elif isa_fun(term):
        return quoted_vars(term[2])
    else:
        raise ValueError(term)
    raise UnreachableError(term)


@memoize_arg
def is_closed(term):
    """A term is closed if all de Bruijn variables are bound."""
    return not any(isa_ivar(v) for v in free_vars(term))


@memoize_arg
def is_defined(term):
    """A term is defined if all nominal variables have been substituted."""
    return not any(isa_nvar(v) for v in free_vars(term))


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
    Y: 6,  # \f. (\x. f(x x)) (\x. f(x x))
    # V: TODO(),
    # A: TODO(),
})


@memoize_arg
def complexity(term):
    """Complexity norm on term.

    Theorem: Modulo alpha conversion and excluding JOIN-terms,
      there are finitely many terms with any fixed complexity.
    Theorem: There are finitely many JOIN-free closed de Bruijn terms
      at any given complexity.

    """
    assert isinstance(term, Term), term
    if isa_atom(term):
        return ATOM_COMPLEXITY[term]
    elif isa_nvar(term) or isa_ivar(term):
        return 1
    elif isa_join(term):
        return max(complexity(term[1]), complexity(term[2]))
    elif isinstance(term, tuple):
        return 1 + max(complexity(arg) for arg in term[1:])
    else:
        raise ValueError(term)
    raise UnreachableError(term)


# ----------------------------------------------------------------------------
# Polish notation

def polish_parse(string, transform=identity):
    """Parse a string from polish notation to a term.

    Args:
      string: a string in polish notation.
      transform: an optional Transform, mapping keyword to builder.

    Returns:
      a term.
    """
    assert isinstance(string, str), type(string)
    assert isinstance(transform, Transform), type(transform)
    tokens = map(intern, string.split())
    tokens.reverse()
    return _polish_parse_tokens(tokens, transform)


def _pop_token(tokens, transform):
    return tokens.pop()


def _pop_int(tokens, transform):
    return int(tokens.pop())


def _polish_parse_tokens(tokens, transform):
    token = tokens.pop()
    try:
        polish_parsers = _PARSERS[token]
    except KeyError:
        if re_keyword.match(token):
            return getattr(transform, token)
        elif re_rank.match(token):
            return IVAR(int(token))
        else:
            return NVAR(token)
    args = tuple(p(tokens, transform) for p in polish_parsers)
    try:
        fun = getattr(transform, token)
    except KeyError:
        return Term.make(token, *args)
    return fun(*args)


_PARSERS = {
    _APP: (_polish_parse_tokens, _polish_parse_tokens),
    _JOIN: (_polish_parse_tokens, _polish_parse_tokens),
    _QUOTE: (_polish_parse_tokens,),
    _ABS: (_polish_parse_tokens,),
    _FUN: (_polish_parse_tokens, _polish_parse_tokens),
    _LESS: (_polish_parse_tokens, _polish_parse_tokens),
    _NLESS: (_polish_parse_tokens, _polish_parse_tokens),
    _EQUAL: (_polish_parse_tokens, _polish_parse_tokens),
}


def polish_print(term):
    assert isinstance(term, Term), term
    tokens = []
    _polish_print_tokens(term, tokens)
    return ' '.join(tokens)


def _polish_print_tokens(term, tokens):
    if isinstance(term, str):
        tokens.append(term)
    elif isinstance(term, tuple):
        if term[0] is _NVAR:
            tokens.append(term[1])
            pos = 2
        elif term[0] is _IVAR:
            tokens.append(str(term[1]))
            pos = 2
        else:
            tokens.append(term[0])
            pos = 1
        for arg in term[pos:]:
            _polish_print_tokens(arg, tokens)
    elif isinstance(term, int):
        tokens.append(str(term))
    else:
        raise ValueError(term)


# ----------------------------------------------------------------------------
# S-Expression notation

@memoize_arg
def to_sexpr(term):
    """Converts from a python term to a python S-expression."""
    assert isinstance(term, Term), term
    if isa_atom(term):
        return term[0]
    elif isa_nvar(term) or isa_ivar(term):
        return term[1]
    head = term
    args = []
    while isa_app(head):
        args.append(to_sexpr(head[2]))
        head = head[1]
    if isa_nvar(head) or isa_ivar(head):
        head = head[1]
    elif head[0] in _keywords:
        for arg in head[-1:0:-1]:
            args.append(to_sexpr(arg))
        head = head[0]
    args.append(head)
    args.reverse()
    return tuple(args)


def from_sexpr(sexpr, transform=identity):
    """Converts from a python S-expression to a python term."""
    assert isinstance(transform, Transform), type(transform)

    # Handle atoms and variables.
    if isinstance(sexpr, str):
        if sexpr in _atoms:
            return getattr(transform, sexpr)
        if re_keyword.match(sexpr):
            raise ValueError('Unrecognized atom: {}'.format(sexpr))
        return NVAR(sexpr)
    if isinstance(sexpr, int):
        return IVAR(sexpr)

    # Handle tuples.
    head = sexpr[0]
    assert isinstance(head, (str, int))
    if head in _keywords:
        arity = _keywords[head]
        head = getattr(transform, head)
        if arity:
            if len(sexpr) < 1 + arity:
                raise ValueError('Too few args to {}: {}'.format(head, sexpr))
            head = head(*(
                from_sexpr(sexpr[1 + i], transform)
                for i in xrange(arity)
            ))
        args = sexpr[1 + arity:]
    elif isinstance(head, int):
        head = IVAR(head)
        args = sexpr[1:]
    else:
        head = NVAR(head)
        args = sexpr[1:]
    for arg in args:
        arg = from_sexpr(arg, transform)
        head = transform.APP(head, arg)
    return head


def sexpr_print_sexpr(sexpr):
    """Prints a python S-expression as a string S-expression."""
    if isinstance(sexpr, str):
        return sexpr
    elif isinstance(sexpr, int):
        return str(sexpr)
    elif isinstance(sexpr, tuple):
        assert len(sexpr) > 1, sexpr
        parts = map(sexpr_print_sexpr, sexpr)
        return '({})'.format(' '.join(parts))
    else:
        raise ValueError(sexpr)


@memoize_arg
def sexpr_print(term):
    """Prints a python term as a string S-expression."""
    assert isinstance(term, Term), term
    sexpr = to_sexpr(term)
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


def sexpr_parse(string, transform=identity):
    """Parse a string from S-expressoin notation to a term.

    Args:
      string: a string in S-expression notation.
      transform: an optional Transform, mapping keyword to builder.

    Returns:
      a term.
    """
    assert isinstance(string, str), type(string)
    assert isinstance(transform, Transform), type(transform)
    sexpr = sexpr_parse_sexpr(string)
    term = from_sexpr(sexpr, transform)
    return term
