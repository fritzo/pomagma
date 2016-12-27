r"""Reduction traces of definable types.

Our goal is to make pomagma.reducer smart enough to prove that I:UNIT,
as in definable_types.text (2016:08:23-25) (Q2):

Desired Theorem: `I : A \a,a',f,x. a(f(a' x))`, where

  copy := \x,y. x y y.
  join := \x,y,z. x(y|z).
  postconj := (\f. f \r,s. <B r, B s>).
  preconj := (\f. f \r,s. <CB s, CB r>).
  compose := (\f,f'. f\r,s. f'\r',s'. <r o r', s' o s>).
  A = A | <I, I> | <copy, join> | <div, BOT> | <BOT, TOP> | <C, C>
        | preconj A | postconj A | compose A A.

"""

from parsable import parsable

from pomagma.reducer.bohm import sexpr_simplify, simplify, try_compute_step
from pomagma.reducer.lib import BOT, TOP, B, C, I, box, pair
from pomagma.reducer.sugar import app, as_code, join_, rec
from pomagma.reducer.syntax import sexpr_print

CB = app(C, B)
div = rec(lambda x: join_(x, app(x, TOP)))
copy = as_code(lambda x, y: app(x, y, y))
join = as_code(lambda x, y, z: app(x, join_(y, z)))
postconj = box(lambda r, s: pair(app(B, r), app(B, s)))
preconj = box(lambda r, s: pair(app(CB, s), app(CB, r)))
compose = as_code(lambda f1, f2:
                  app(f1, lambda r1, s1:
                      app(f2, lambda r2, s2:
                          pair(app(B, r1, r2), app(B, s2, s1)))))


# A = A | <I, I> | <copy, join> | <div, BOT> | <BOT, TOP> | <C, C>
#       | preconj A | postconj A | compose A A.
PARTS = {
    'base': as_code(lambda a: pair(I, I)),
    'copy': as_code(lambda a: pair(copy, join)),
    'div': as_code(lambda a: pair(div, BOT)),
    'bot': as_code(lambda a: pair(BOT, TOP)),
    'swap': as_code(lambda a: pair(C, C)),
    'preconj': preconj,
    'postconj': postconj,
    'compose': as_code(lambda a: app(compose, a, a)),
}


def build_A(*part_names):
    return rec(join_(*(PARTS[name] for name in part_names)))


unit_sig = as_code(lambda r, s, f, x: app(r, app(f, app(s, x))))

default_type = '(FUN r (FUN s (FUN f (FUN x (r (f (s x)))))))'
default_inhab = '(FUN x x)'


@parsable
def trace(*part_names, **kwargs):
    """Trace an approximation to A.

    Possible names: all base copy div bot swap preconj postconj compose

    Kwargs:
      steps = 10
      type = '(FUN r (FUN s (FUN f (FUN x (r (f (s x)))))))'
      inhab = '(FUN x x)'
    """
    # Construct an approximation of A with only a few parts.
    if 'all' in part_names:
        part_names = PARTS.keys()
    for name in part_names:
        assert name in PARTS, name
    A = simplify(build_A(*part_names))
    print('A = {}'.format(sexpr_print(A)))

    # Cast a candidate inhabitant via the defined type.
    type_ = sexpr_simplify(kwargs.get('type', default_type))
    inhab = sexpr_simplify(kwargs.get('inhab', default_inhab))
    code = simplify(app(A, type_, inhab))
    print('0\t{}'.format(sexpr_print(code)))

    # Print a reduction sequence.
    steps = int(kwargs.get('steps', 10))
    for step in xrange(steps):
        code = try_compute_step(code)
        if code is None:
            print '--- Normalized ---'
            return
        print('{}\t{}'.format(1 + step, sexpr_print(code)))
    print '... Not normalized ...'


if __name__ == '__main__':
    parsable()
