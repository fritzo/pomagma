from logpy.dispatch import dispatch
from pomagma.compiler.expressions import Expression
import logpy


@dispatch(Expression, Expression, dict)
def _unify(lhs, rhs, subst):
    raise NotImplementedError('implement constraint solving over obs')


def parse_constraint(constraint, free_vars):
    assert isinstance(constraint, Expression), constraint
    assert isinstance(free_vars, dict), free_vars
    raise NotImplementedError('return something compatible with logpy')


def solve(var, constraints, count=10):
    assert isinstance(var, basestring), var
    for constraint in constraints:
        assert isinstance(constraint, Expression), constraint
    free_vars = set(v for c in constraints for v in constraints.vars())
    assert var in free_vars
    logpy_vars = {name: var() for name in free_vars}
    goals = [parse_constraint(c, logpy_vars) for c in constraints]
    return logpy.run(count, logpy_vars[var], *goals)
