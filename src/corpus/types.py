from pomagma.compiler.expressions import Expression_0
from pomagma.compiler.expressions import Expression_2
from pomagma.corpus import Corpus

I = Expression_0('I')
APP = Expression_2('APP')
FUN = Expression_2('FUN')
FIX = Expression_2('FIX')

corpus = Corpus()


def match(head, body):
    head = map(Expression_0, head.split())
    body = Expression_0(body)
    var, args = head[0], head[1:]
    for arg in reversed(args):
        body = FUN(arg, body)
    return var, body


def let(head, body):
    var, body = match(head, body)
    corpus.insert(var, body)


def fix(head, body):
    var, body = match(head, body)
    body = FIX(var, body)
    corpus.insert(var, body)


# This is totally unreadable.
let('pair f x y', 'APP APP f x y')
let('raise x y', 'x')
let('lower x', 'APP x TOP')
let('push x', 'APP x BOT')
let('pull x', 'APP x BOT')
let('conj f g x', 'COMP COMP g x f')
fix('forall',
    '''
    JOIN APP APP pair I I
    JOIN APP APP pair push pull
    JOIN APP APP pair lower raise
    JOIN APP forall FUN r1 FUN s1
         APP forall FUN r2 FUN s2
         APP APP pair COMP r1 r2 COMP s2 s1
    JOIN APP forall FUN r1 FUN s1
         APP forall FUN r2 FUN s2
         APP APP pair APP APP conj r1 r2 APP APP conj s2 s1
    HOLE
    ''')

let('forall.ii',
    'LESS APP APP pair I I forall')

# This is in <section, retract> orientation.
r'''
raise := (\x,-. x).
lower := (\x. x T).
pull := (\x,y. x|div y).
push := (\x. x _).
A := (Y\s. <I, I>
         | <raise, lower>
         | <pull, push>
         | (s\a,a'. s\b,b'. <a*b, b'*a'>)
         | (s\a,a'. s\b,b'. <(a'->b), (a->b')>)
         | HOLE).
'''

# This is in <retract, section> orientation.
r'''
let raise x y = x.
let lower x = x T.
let pull x y = x|div y.
let push x = x _.
let forall = <I, I>
           | <lower, raise>
           | <push, pull>
           | (forall \a,a'. forall \b,b'. <a*b, b'*a'>)
           | (forall \a,a'. forall \b,b'. <a'->b, a->b'>)
           | ?.
'''
