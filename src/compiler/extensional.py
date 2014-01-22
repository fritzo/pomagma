import itertools
from pomagma.compiler.util import TODO, logger, inputs, methodof
from pomagma.compiler.signature import is_positive
from pomagma.compiler.expressions import Expression
from pomagma.compiler.sequents import Sequent

I = Expression('I')
K = Expression('K')
J = Expression('J')
R = Expression('R')
B = Expression('B')
C = Expression('C')
W = Expression('W')
S = Expression('S')
BOT = Expression('BOT')
TOP = Expression('TOP')
APP = lambda x, y: Expression('APP', x, y)
COMP = lambda x, y: Expression('COMP', x, y)
JOIN = lambda x, y: Expression('JOIN', x, y)
RAND = lambda x, y: Expression('RAND', x, y)


class AbstractionFailed(Exception):
    pass


@methodof(Expression)
def abstract(self, var):
    assert isinstance(var, Expression)
    assert var.is_var()
    if self.is_var():
        if self == var:
            return I
        else:
            return APP(K, self)
    elif self.is_fun():
        name = self.name
        if var not in self.vars:
            return APP(K, self)
        elif name == 'APP':
            # IKCSW-compose-eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                lhs_abs = lhs.abstract(var)
                if var in rhs.vars:
                    if rhs == var:
                        return APP(W, lhs_abs)
                    else:
                        return APP(APP(S, lhs_abs), rhs.abstract(var))
                else:
                    return APP(APP(C, lhs_abs), rhs)
            else:
                assert var in rhs.vars
                if rhs == var:
                    return lhs
                else:
                    return COMP(lhs, rhs.abstract(var))
        elif name == 'COMP':
            # KBCS-compose-eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                lhs_abs = lhs.abstract(var)
                if var in rhs.vars:
                    return APP(APP(S, COMP(B, lhs_abs)), rhs.abstract(var))
                else:
                    if lhs == var:
                        return APP(APP(C, B), rhs)
                    else:
                        return COMP(APP(APP(C, B), rhs), lhs_abs)
            else:
                assert var in rhs.vars
                if rhs == var:
                    return APP(B, lhs)
                else:
                    return COMP(APP(B, lhs), rhs.abstract(var))
        elif name == 'JOIN':
            # K-compose-eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                if var in rhs.vars:
                    return JOIN(lhs.abstract(var), rhs.abstract(var))
                elif lhs == var:
                    return APP(J, rhs)
                else:
                    return COMP(APP(J, rhs), lhs.abstract(var))
            else:
                assert var in rhs.vars
                if rhs == var:
                    return APP(J, lhs)
                else:
                    return COMP(APP(J, lhs), rhs.abstract(var))
        elif name == 'RAND':
            # K-compose-eta abstraction
            lhs, rhs = self.args
            if var in lhs.vars:
                if var in rhs.vars:
                    return RAND(lhs.abstract(var), rhs.abstract(var))
                elif lhs == var:
                    return APP(R, rhs)
                else:
                    return COMP(APP(R, rhs), lhs.abstract(var))
            else:
                assert var in rhs.vars
                if rhs == var:
                    return APP(R, lhs)
                else:
                    return COMP(APP(R, lhs), rhs.abstract(var))
        else:
            raise AbstractionFailed
    elif self.is_rel():
        args = [arg.abstract(var) for arg in self.args]
        return Expression(self.name, *args)
    else:
        raise ValueError('bad expression: %s' % self.name)


class RequireVariable(Exception):
    pass


class SkipValidation(Exception):
    pass


def get_fresh(bound):
    for name in 'abcdefghijklmnopqrstuvwxyz':
        fresh = Expression(name)
        if fresh not in bound:
            return fresh
    raise NotImplementedError('Exceeded fresh variable limit')


def pop_arg(args):
    if args:
        return args[0], args[1:]
    else:
        raise RequireVariable


def head_normalize(expr, *args):
    if expr.is_var():
        return [expr] + list(args)
    else:
        assert expr.is_fun(), expr
        name = expr.name
        if name == 'APP':
            lhs, rhs = expr.args
            return head_normalize(lhs, rhs, *args)
        elif name == 'COMP':
            lhs, rhs = expr.args
            arg0, args = pop_arg(args)
            return head_normalize(lhs, APP(rhs, arg0), *args)
        elif name in ['BOT', 'TOP']:
            return [expr]
        elif name == 'I':
            arg0, args = pop_arg(args)
            return head_normalize(arg0, *args)
        elif name == 'K':
            arg0, args = pop_arg(args)
            arg1, args = pop_arg(args)
            return head_normalize(arg0, *args)
        elif name == 'B':
            arg0, args = pop_arg(args)
            arg1, args = pop_arg(args)
            arg2, args = pop_arg(args)
            return head_normalize(arg0, APP(arg1, arg2), *args)
        elif name == 'C':
            arg0, args = pop_arg(args)
            arg1, args = pop_arg(args)
            arg2, args = pop_arg(args)
            return head_normalize(arg0, arg2, arg1, *args)
        elif name == 'W':
            arg0, args = pop_arg(args)
            arg1, args = pop_arg(args)
            return head_normalize(arg0, arg1, arg1, *args)
        elif name == 'S':
            arg0, args = pop_arg(args)
            arg1, args = pop_arg(args)
            arg2, args = pop_arg(args)
            return head_normalize(arg0, arg2, APP(arg1, arg2), *args)
        elif name == 'CI':
            return head_normalize(C, I, *args)
        elif name == 'CB':
            return head_normalize(C, B, *args)
        elif name in ['Y', 'J', 'JOIN', 'R', 'RAND', 'U', 'V', 'P', 'A']:
            raise SkipValidation
        else:
            raise TODO('head normalize %s expressions' % name)


def validate(expr):
    assert expr.is_rel(), expr
    assert expr.name in ['LESS', 'EQUAL']
    if expr.name != 'EQUAL':
        print 'WARNING: not validating {0}'.format(expr)
        return
    while True:
        try:
            lhs, rhs = expr.args
            lhs = head_normalize(lhs)
            rhs = head_normalize(rhs)
            assert len(lhs) == len(rhs),\
                'Failed to validate\n  {0}\nbecause\n  {1} != {2}'.format(
                    expr, lhs, rhs)
            assert lhs[0] == rhs[0],\
                'Failed to validate\n  {0}\nbecause  \n{1} != {2}'.format(
                    expr, lhs[0], rhs[0])
            for args in zip(lhs[1:], rhs[1:]):
                validate(Expression(expr.name, *args))
            break
        except RequireVariable:
            lhs, rhs = expr.args
            fresh = get_fresh(expr.vars)
            lhs = APP(lhs, fresh)
            rhs = APP(rhs, fresh)
            expr = Expression(expr.name, lhs, rhs)
        except SkipValidation:
            print 'WARNING: not validating {0}'.format(expr)
            return


@inputs(Expression)
def iter_eta_substitutions(expr):
    '''
    Iterate over Hindley-style substitutions:
        [x/x], [x/a], [x/APP x a] (and maybe [x/COMP x a])
    '''
    varlist = list(expr.vars)
    fresh = get_fresh(expr.vars)
    for cases in itertools.product(range(3), repeat=len(varlist)):
        result = expr
        for var, case in zip(varlist, cases):
            if case == 0:
                'do nothing'
            elif case == 1:
                result = result.substitute(var, fresh)
            elif case == 2:
                result = result.substitute(var, APP(var, fresh))
            # elif case == 3:
            #    result = result.substitute(var, COMP(var, fresh))
        if any(cases):
            yield result.abstract(fresh)
        else:
            yield result
    raise StopIteration


def iter_subsets(set_):
    list_ = list(set_)
    for cases in itertools.product([0, 1], repeat=len(list_)):
        yield set(x for (x, case) in itertools.izip(list_, cases) if case)
    raise StopIteration


@inputs(Expression)
def iter_closure_maps(expr):
    '''
    Iterate over all closing abstractions, including variable coincidence
    '''
    if not expr.vars:
        yield expr
    else:
        for varset in iter_subsets(expr.vars):
            if varset:
                var = varset.pop()
                abstracted = expr
                for other in varset:
                    abstracted = abstracted.substitute(other, var)
                abstracted = abstracted.abstract(var)
                for result in iter_closure_maps(abstracted):
                    yield result
    raise StopIteration


@inputs(Expression)
def iter_closure_permutations(expr):
    '''
    Iterate over all closing permutations
    '''
    if not expr.vars:
        yield expr
    else:
        for var in expr.vars:
            abstracted = expr.abstract(var)
            for result in iter_closure_maps(abstracted):
                yield result
    raise StopIteration


@inputs(Expression)
def iter_closures(expr):
    if expr.name == 'OPTIONALLY':
        expr = expr.args[0]
    try:
        assert expr.is_rel(), expr
        lhs, rhs = expr.args
        if not expr.vars:
            yield expr
        elif is_positive(expr.name):
            for expr2 in iter_eta_substitutions(expr):
                assert expr2.is_rel(), expr2
                for expr3 in iter_closure_maps(expr2):
                    assert expr3.is_rel(), expr3
                    yield expr3
        else:
            for expr2 in iter_closure_permutations(expr):
                yield expr2
    except AbstractionFailed:
        pass
    raise StopIteration


@inputs(Sequent)
def derive_facts(rule):
    facts = set()
    if len(rule.antecedents) == 0 and len(rule.succedents) == 1:
        expr = iter(rule.succedents).next()
        for derived in iter_closures(expr):
            lhs, rhs = derived.args
            if lhs != rhs:
                assert derived.is_rel()
                facts.add(derived)
        facts = sorted(list(facts), key=lambda expr: len(expr.polish))
        logger('derived {0} facts from {1}'.format(len(facts), expr))
    return facts
