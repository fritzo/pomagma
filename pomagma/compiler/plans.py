import math

from pomagma.compiler.expressions import Expression_1
from pomagma.compiler.util import log_sum_exp, set_with
from pomagma.util.hashcons import HashConsArgsMeta


def assert_in(element, set_):
    assert element in set_, (element, set_)


def assert_not_in(element, set_):
    assert element not in set_, (element, set_)


def assert_subset(subset, set_):
    assert subset <= set_, (subset, set_)


OBJECT_COUNT = 1e4  # optimize for this many obs
LOGIC_COST = OBJECT_COUNT / 64.0  # perform logic on 64-bit words
LOG_OBJECT_COUNT = math.log(OBJECT_COUNT)

UNKNOWN = Expression_1("UNKNOWN")


def add_costs(costs):
    return log_sum_exp(*(LOG_OBJECT_COUNT * c for c in costs)) / LOG_OBJECT_COUNT


class Plan(metaclass=HashConsArgsMeta):
    __slots__ = ["_args", "_cost", "_rank"]

    def __init__(self, *args):
        self._args = args
        self._cost = None
        self._rank = None

    @property
    def cost(self):
        if self._cost is None:
            self._cost = math.log(self.op_count()) / LOG_OBJECT_COUNT
        return self._cost

    @property
    def rank(self):
        if self._rank is None:
            s = repr(self)
            self._rank = self.cost, len(s), s
        return self._rank

    def __lt__(self, other):
        return self.rank < other.rank

    def permute_symbols(self, perm):
        return self.__class__(*(a.permute_symbols(perm) for a in self._args))


class Iter(Plan):
    __slots__ = ["_repr", "var", "body", "tests", "lets", "stack"]

    def __init__(self, var, body):
        Plan.__init__(self, var, body)
        assert var.is_var(), var
        assert isinstance(body, Plan), body
        self._repr = None
        self.var = var
        self.body = body
        self.tests = []
        self.lets = {}
        self.stack = set()
        self.optimize()

    def add_test(self, test):
        assert isinstance(test, Test), "add_test arg is not a Test"
        self.tests.append(test.expr)
        self.stack.add(test)

    def add_let(self, let):
        assert isinstance(let, Let), "add_let arg is not a Let"
        assert let.var not in self.lets, "add_let var is not in Iter.lets"
        self.lets[let.var] = let.expr
        self.stack.add(let)

    def __repr__(self):
        if self._repr is None:
            # Optimized:
            # tests = ['if {}'.format(t) for t in self.tests]
            # lets = ['let {}'.format(l) for l in sorted(self.lets.keys())]
            # self._repr = 'for {0}: {1}'.format(
            #     ' '.join([str(self.var)] + tests + lets),
            #     self.body)
            self._repr = f"for {self.var}: {self.body}"
        return self._repr

    def validate(self, bound):
        assert_not_in(self.var, bound)
        bound = set_with(bound, self.var)
        for test in self.tests:
            assert_subset(test.vars, bound)
        for var, expr in list(self.lets.items()):
            assert_subset(expr.vars, bound)
            assert_not_in(var, bound)
        self.body.validate(bound)

    def op_count(self, stack=None):
        logic_cost = LOGIC_COST * (len(self.tests) + len(self.lets))
        object_count = OBJECT_COUNT
        for test_or_let in self.stack:
            object_count *= test_or_let.prob()
        let_cost = len(self.lets)
        body_cost = self.body.op_count(stack=self.stack)
        return logic_cost + object_count * (let_cost + body_cost)

    def optimize(self):
        node = self.body
        new_lets = set()
        while isinstance(node, Test | Let):
            if isinstance(node, Let):
                new_lets.add(node.var)
            expr = node.expr
            while expr.name == "UNKNOWN":
                expr = expr.args[0]
            optimizable = (
                self.var in expr.vars
                and expr.vars.isdisjoint(new_lets)
                and sum(1 for arg in expr.args if self.var == arg) == 1
                and sum(1 for arg in expr.args if self.var in arg.vars) == 1
                and (isinstance(node, Let) or expr.is_rel())
            )
            if optimizable:
                if isinstance(node, Test):
                    self.add_test(node)
                else:
                    self.add_let(node)
            node = node.body


# TODO injective function inverse need not be iterated
class IterInvInjective(Plan):
    __slots__ = ["fun", "value", "var", "body"]

    def __init__(self, fun, body):
        Plan.__init__(self, fun, body)
        assert fun.arity == "InjectiveFunction"
        self.fun = fun.name
        self.value = fun.var
        (self.var,) = fun.args
        self.body = body

    def __repr__(self):
        return f"for {self.fun} {self.var}: {self.body}"

    def validate(self, bound):
        assert_in(self.value, bound)
        assert_not_in(self.var, bound)
        self.body.validate(set_with(bound, self.var))

    def op_count(self, stack=None):
        return 4.0 + 0.5 * self.body.op_count()  # amortized


class IterInvBinary(Plan):
    __slots__ = ["fun", "value", "var1", "var2", "body"]

    def __init__(self, fun, body):
        Plan.__init__(self, fun, body)
        assert fun.arity in ["BinaryFunction", "SymmetricFunction"]
        self.fun = fun.name
        self.value = fun.var
        self.var1, self.var2 = fun.args
        self.body = body

    def __repr__(self):
        return f"for {self.fun} {self.var1} {self.var2}: {self.body}"

    def validate(self, bound):
        assert_in(self.value, bound)
        assert_not_in(self.var1, bound)
        assert_not_in(self.var2, bound)
        self.body.validate(set_with(bound, self.var1, self.var2))

    def op_count(self, stack=None):
        return 4.0 + 0.25 * OBJECT_COUNT * self.body.op_count()  # amortized


class IterInvBinaryRange(Plan):
    __slots__ = ["fun", "value", "var1", "var2", "lhs_fixed", "body"]

    def __init__(self, fun, fixed, body):
        Plan.__init__(self, fun, fixed, body)
        assert fun.arity in ["BinaryFunction", "SymmetricFunction"]
        self.fun = fun.name
        self.value = fun.var
        self.var1, self.var2 = fun.args
        assert self.var1 != self.var2
        assert self.var1 == fixed or self.var2 == fixed
        self.lhs_fixed = fixed == self.var1
        self.body = body

    def __repr__(self):
        if self.lhs_fixed:
            return f"for {self.fun} ({self.var1}) {self.var2}: {self.body}"
        return f"for {self.fun} {self.var1} ({self.var2}): {self.body}"

    def validate(self, bound):
        assert self.value in bound
        if self.lhs_fixed:
            assert_in(self.var1, bound)
            assert_not_in(self.var2, bound)
            self.body.validate(set_with(bound, self.var2))
        else:
            assert_in(self.var2, bound)
            assert_not_in(self.var1, bound)
            self.body.validate(set_with(bound, self.var1))

    def op_count(self, stack=None):
        return 4.0 + 0.5 * self.body.op_count()  # amortized


class Let(Plan):
    __slots__ = ["var", "expr", "body"]

    def __init__(self, expr, body):
        Plan.__init__(self, expr, body)
        assert isinstance(body, Plan)
        assert expr.is_fun()
        self.var = expr.var
        self.expr = expr
        self.body = body

    def __repr__(self):
        return f"let {self.var}: {self.body}"

    def validate(self, bound):
        assert_subset(self.expr.vars, bound)
        assert_not_in(self.var, bound)
        self.body.validate(set_with(bound, self.var))

    __probs = {"NullaryFunction": 0.9}

    def prob(self):
        return self.__probs.get(self.expr.arity, 0.1)

    def op_count(self, stack=None):
        if stack and self in stack:
            return self.body.op_count(stack=stack)
        return 1.0 + self.prob() * self.body.op_count(stack=stack)


class Test(Plan):
    __slots__ = ["expr", "body"]

    def __init__(self, expr, body):
        Plan.__init__(self, expr, body)
        assert not expr.is_var()
        assert isinstance(body, Plan)
        self.expr = expr
        self.body = body

    def __repr__(self):
        return f"if {self.expr}: {self.body}"

    def validate(self, bound):
        assert_subset(self.expr.vars, bound)
        self.body.validate(bound)

    __probs = {"NLESS": 0.9}

    def prob(self):
        return self.__probs.get(self.expr.name, 0.1)

    def op_count(self, stack=None):
        if stack and self in stack:
            return self.body.op_count(stack=stack)
        return 1.0 + self.prob() * self.body.op_count(stack=stack)


class Ensure(Plan):
    __slots__ = ["expr"]

    def __init__(self, expr):
        Plan.__init__(self, expr)
        assert expr.args, ("expr is not compound", expr)
        self.expr = expr

    def __repr__(self):
        return f"ensure {self.expr}"

    def validate(self, bound):
        assert_subset(self.expr.vars, bound)

    def op_count(self, stack=None):
        fun_count = 0
        if self.expr.name == "EQUATION":
            for arg in self.expr.args:
                if arg.is_fun():
                    fun_count += 1
        return [1.0, 1.0 + 0.5 * 1.0, 2.0 + 0.75 * 1.0][fun_count]
