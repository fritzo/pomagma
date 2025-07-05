import contextlib

from pomagma.compiler import compiler, signature
from pomagma.compiler.expressions import Expression, NotNegatable, try_negate_name
from pomagma.compiler.plans import add_costs
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.util import methodof

MIN_SPLIT_COST = 1.5  # above which we split the outermost for loop


def get_set_var(name, args):
    return "_".join([name] + [a.var.name.rstrip("_") for a in args])


@methodof(compiler.Iter, "program")
def Iter_program(self, program, stack=None, poll=None):
    pos_sets = []
    neg_sets = []
    for_ = f"FOR_ALL {self.var}"

    for test in self.tests:
        if test.name == "UNKNOWN":
            modifier = "UNKNOWN"
            test = test.args[0]
        else:
            modifier = "POS"
        set_var = get_set_var(test.name, test.args)
        if modifier == "POS" and test.arity == "UnaryRelation":
            for_ = f"FOR_UNARY_RELATION {test.name} {self.var}"
            pos_set = f"LETS_UNARY_RELATION {test.name} {set_var}"
            pos_sets.append((set_var, pos_set))
        elif modifier == "POS" and test.arity == "BinaryRelation":
            lhs, rhs = test.args
            assert lhs != rhs, lhs
            PARITY = "LHS" if self.var == rhs else "RHS"
            for_ = f"FOR_BINARY_RELATION_{PARITY} {test.name} {lhs} {rhs}"
            pos_set = f"LETS_BINARY_RELATION_{PARITY} {test.name} {set_var if self.var == lhs else lhs} {set_var if self.var == rhs else rhs}"
            pos_sets.append((set_var, pos_set))
        elif modifier == "UNKNOWN" and test.arity == "UnaryRelation":
            for_ = None
            neg_set = f"LETS_UNARY_RELATION {test.name} {set_var}"
            neg_sets.append((set_var, neg_set))
        elif modifier == "UNKNOWN" and test.arity == "BinaryRelation":
            for_ = None
            lhs, rhs = test.args
            assert lhs != rhs, lhs
            PARITY = "LHS" if self.var == rhs else "RHS"
            neg_set = f"LETS_BINARY_RELATION_{PARITY} {test.name} {set_var if self.var == lhs else lhs} {set_var if self.var == rhs else rhs}"
            neg_sets.append((set_var, neg_set))
        else:
            raise ValueError(f"invalid modifier,arity: {modifier},{test.arity}")

    for var, expr in sorted(self.lets.items()):
        assert self.var in expr.args, f"{self.var} not in {expr.args}"
        set_var = expr.var.name
        if expr.arity == "InjectiveFunction":
            for_ = f"FOR_INJECTIVE_FUNCTION {expr.name} {self.var} {var}"
            pos_set = f"LETS_INJECTIVE_FUNCTION {expr.name} {set_var}"
        elif expr.arity == "BinaryFunction":
            lhs, rhs = expr.args
            assert lhs != rhs, lhs
            if self.var == lhs:
                for_ = (
                    f"FOR_BINARY_FUNCTION_RHS {expr.name} {lhs} {rhs} {expr.var.name}"
                )
                pos_set = f"LETS_BINARY_FUNCTION_RHS {expr.name} {set_var} {rhs}"
            else:
                for_ = (
                    f"FOR_BINARY_FUNCTION_LHS {expr.name} {lhs} {rhs} {expr.var.name}"
                )
                pos_set = f"LETS_BINARY_FUNCTION_LHS {expr.name} {lhs} {set_var}"
        elif expr.arity == "SymmetricFunction":
            lhs, rhs = expr.args
            assert lhs != rhs, lhs
            fixed = rhs if self.var == lhs else lhs
            for_ = f"FOR_SYMMETRIC_FUNCTION_LHS {expr.name} {fixed} {self.var} {expr.var.name}"
            pos_set = f"LETS_SYMMETRIC_FUNCTION_LHS {expr.name} {fixed} {set_var}"
        else:
            raise ValueError(f"invalid arity {expr.arity}")
        pos_sets.append((set_var, pos_set))

    if len(pos_sets) <= 1 and len(neg_sets) == 0:
        program.append(for_)
        if poll:
            program.append(f"IF_BLOCK {self.var}")
    else:
        for_ = "FOR{pos}{neg} {val}".format(
            pos="_POS" * len(pos_sets), neg="_NEG" * len(neg_sets), val=self.var
        )
        for set_var, pos_set in pos_sets + neg_sets:
            program.append(pos_set)
            for_ += f" {set_var}"
        program.append(for_)
        if poll:
            program.append(f"IF_BLOCK {self.var}")
        for var, expr in sorted(self.lets.items()):
            arity = expr.arity
            ARITY = arity.replace("Function", "").upper()
            assert ARITY in ["INJECTIVE", "BINARY", "SYMMETRIC"], ARITY
            args = [a.name for a in expr.args]
            line = "LET_{ARITY}_FUNCTION {fun} {args} {val}".format(
                ARITY=ARITY, fun=expr.name, args=" ".join(args), val=var
            )
            program.append(line)
    self.body.program(program, stack=self.stack)


@methodof(compiler.IterInvInjective, "program")
def IterInvInjective_program(self, program, stack=None, poll=None):
    program.append(f"FOR_INJECTIVE_FUNCTION_INVERSE {self.fun} {self.var} {self.value}")
    self.body.program(program, poll=poll)


@methodof(compiler.IterInvBinary, "program")
def IterInvBinary_program(self, program, stack=None, poll=None):
    ARITY = signature.get_arity(self.fun).replace("Function", "").upper()
    program.append(
        f"FOR_{ARITY}_FUNCTION_VAL {self.fun} {self.var1} {self.var2} {self.value}"
    )
    if poll:
        raise NotImplementedError("cannot poll IterInvBinary")
        # program.append('IF_BLOCK {val}'.format(val=self.var1))  # arbitrary
    self.body.program(program)


@methodof(compiler.IterInvBinaryRange, "program")
def IterInvBinaryRange_program(self, program, stack=None, poll=None):
    PARITY = "LHS" if self.lhs_fixed else "RHS"
    ARITY = signature.get_arity(self.fun).replace("Function", "").upper()

    line = f"FOR_{ARITY}_FUNCTION_{PARITY}_VAL {self.fun} {self.var1} {self.var2} {self.value}"
    program.append(line)
    if poll:
        raise NotImplementedError("cannot poll IterInvBinaryRange")
        # program.append('IF_BLOCK {val}'.format(val=var))  # arbitrary
    self.body.program(program)


@methodof(compiler.Let, "program")
def Let_program(self, program, stack=None, poll=None):
    if not (stack and self in stack):
        arity = self.expr.arity
        args = [arg.name for arg in self.expr.args]
        if arity == "NullaryFunction":
            line = f"FOR_NULLARY_FUNCTION {self.expr.name} {self.var}"
        elif arity == "InjectiveFunction":
            line = f"FOR_INJECTIVE_FUNCTION_KEY {self.expr.name} {args[0]} {self.var}"
        elif arity == "BinaryFunction":
            line = f"FOR_BINARY_FUNCTION_LHS_RHS {self.expr.name} {args[0]} {args[1]} {self.var}"
        elif arity == "SymmetricFunction":
            line = f"FOR_SYMMETRIC_FUNCTION_LHS_RHS {self.expr.name} {args[0]} {args[1]} {self.var}"
        else:
            raise ValueError(f"unknown arity: {arity}")
        program.append(line)
    self.body.program(program, stack=stack, poll=poll)


@methodof(compiler.Test, "program")
def Test_program(self, program, stack=None, poll=None):
    if not (stack and self in stack):
        arity = self.expr.arity
        args = [arg.name for arg in self.expr.args]
        if self.expr.name == "EQUAL":
            line = f"IF_EQUAL {self.expr.args[0]} {self.expr.args[1]}"
        elif arity == "UnaryRelation":
            line = f"IF_UNARY_RELATION {self.expr.name} {args[0]}"
        elif arity == "BinaryRelation":
            line = f"IF_BINARY_RELATION {self.expr.name} {args[0]} {args[1]}"
        elif arity == "NullaryFunction":
            line = f"IF_NULLARY_FUNCTION {self.expr.name} {self.expr.var.name}"
        elif arity == "InjectiveFunction":
            line = (
                f"IF_INJECTIVE_FUNCTION {self.expr.name} {args[0]} {self.expr.var.name}"
            )
        elif arity == "BinaryFunction":
            line = f"IF_BINARY_FUNCTION {self.expr.name} {args[0]} {args[1]} {self.expr.var.name}"
        elif arity == "SymmetricFunction":
            line = f"IF_SYMMETRIC_FUNCTION {self.expr.name} {args[0]} {args[1]} {self.expr.var.name}"
        else:
            raise ValueError(f"unknown arity: {arity}")
        program.append(line)
    self.body.program(program, stack=stack, poll=poll)


@methodof(compiler.Ensure, "program")
def Ensure_program(self, program, stack=None, poll=None):
    expr = self.expr
    args = [arg if arg.args else arg.var for arg in expr.args]
    if all(arg.is_var() for arg in args):
        arity = self.expr.arity
        if self.expr.name == "EQUAL":
            line = f"INFER_EQUAL {args[0]} {args[1]}"
        elif arity == "UnaryRelation":
            line = f"INFER_UNARY_RELATION {self.expr.name} {args[0]}"
        elif arity == "BinaryRelation":
            line = f"INFER_BINARY_RELATION {self.expr.name} {args[0]} {args[1]}"
        else:
            raise ValueError(f"unknown arity: {arity}")

    elif any(arg.is_var() for arg in args):
        assert self.expr.name == "EQUAL", self.expr.name

        if args[0].is_var():
            var, expr = args
        else:
            expr, var = args
        args = [arg.var.name for arg in expr.args]
        ARITY = expr.arity.replace("Function", "").upper()
        line = "INFER_{ARITY}_FUNCTION {fun} {args} {var}".format(
            ARITY=ARITY, fun=expr.name, args=" ".join(args), var=var.name
        )
    else:
        assert self.expr.name == "EQUAL", self.expr.name

        lhs, rhs = args
        if (len(rhs.args), rhs.name) < (len(lhs.args), lhs.name):
            lhs, rhs = rhs, lhs
        line = "INFER_{ARITY1}_{ARITY2} {fun1} {args1} {fun2} {args2}".format(
            ARITY1=lhs.arity.replace("Function", "").upper(),
            ARITY2=rhs.arity.replace("Function", "").upper(),
            fun1=lhs.name,
            fun2=rhs.name,
            args1=" ".join(a.var.name for a in lhs.args),
            args2=" ".join(a.var.name for a in rhs.args),
        )

    program.append(line)


def write_full_programs(programs, sequents, can_parallelize=True):
    full_tasks = []
    for sequent in sequents:
        for cost, seq, plan in compiler.compile_full(sequent):
            full_tasks.append((cost, sequent, seq, plan))
    full_tasks.sort()
    for plan_id, (cost, sequent, seq, plan) in enumerate(full_tasks):
        poll = can_parallelize and (cost >= MIN_SPLIT_COST)
        programs += [
            "",
            f"# plan {plan_id}: cost = {cost:0.1f}",
            f"# using {sequent}",
            f"# infer {seq}",
        ]
        if poll:
            programs.append("FOR_BLOCK")
        plan.program(programs, poll=poll)


def write_event_programs(programs, sequents):
    event_tasks = {}
    for sequent in sequents:
        for event in compiler.get_events(sequent):
            name = "Variable" if event.is_var() else event.name
            plans = sorted(compiler.compile_given(sequent, event))
            cost = add_costs(c for (c, _, _) in plans)
            tasks = event_tasks.setdefault(name, [])
            tasks.append((cost, event, sequent, plans))

    group_tasks = {}
    for name, tasks in list(event_tasks.items()):
        groupname = signature.get_arity(name)
        group_tasks.setdefault(groupname, {})[name] = sorted(tasks)

    group_tasks = sorted(group_tasks.items())
    group_id = 0
    for groupname, group in group_tasks:
        group = sorted(group.items())
        arity = signature.get_arity(group[0][0])

        for eventname, tasks in group:
            total_cost = add_costs(c for (c, _, _, _) in tasks)
            programs += [
                "",
                "# " + "-" * 76,
                f"# plans {group_id}.*: total cost = {total_cost:0.1f}",
                f"# given {eventname}",
            ]

            plan_id = 0
            for _, event, sequent, plans in tasks:
                diagonal = len(event.args) == 2 and event.args[0] == event.args[1]
                if diagonal:
                    lhs = event.args[0]
                    assert lhs.arity == "Variable"
                    rhs = Expression(lhs.name + "_")
                    event = Expression(event.name, lhs, rhs)

                if arity == "Variable":
                    given = f"GIVEN_EXISTS {event.name}"
                elif arity == "UnaryRelation":
                    given = f"GIVEN_UNARY_RELATION {event.name} {event.args[0]}"
                elif arity == "BinaryRelation":
                    given = f"GIVEN_BINARY_RELATION {event.name} {event.args[0]} {event.args[1]}"
                elif arity == "NullaryFunction":
                    given = f"GIVEN_NULLARY_FUNCTION {event.name} {event.var.name}"
                elif arity == "InjectiveFunction":
                    given = f"GIVEN_INJECTIVE_FUNCTION {event.name} {event.args[0]} {event.var.name}"
                elif arity == "BinaryFunction":
                    given = f"GIVEN_BINARY_FUNCTION {event.name} {event.args[0]} {event.args[1]} {event.var.name}"
                elif arity == "SymmetricFunction":
                    given = f"GIVEN_SYMMETRIC_FUNCTION {event.name} {event.args[0]} {event.args[1]} {event.var.name}"
                else:
                    raise ValueError(f"invalid arity: {arity}")
                header = [given]

                if diagonal:
                    header.append(f"IF_EQUAL {event.args[0]} {event.args[1]}")

                for cost, seq, plan in plans:
                    programs += [
                        "",
                        f"# plan {group_id}.{plan_id}: cost = {cost:0.1f}",
                        f"# using {sequent}",
                        f"# infer {seq}",
                    ]
                    programs += header
                    plan.program(programs)
                    plan_id += 1

            group_id += 1


def get_symbols_used_in(sequents, exprs):
    symbols = {}
    tokens = set()
    for seq in sequents:
        assert isinstance(seq, Sequent), seq
        for expr in seq.antecedents | seq.succedents:
            tokens |= set(expr.polish.split())
    for expr in exprs:
        assert isinstance(expr, Expression), expr
        tokens |= set(expr.polish.split())
    for token in list(tokens):
        if signature.get_arity(token) in signature.RELATION_ARITIES:
            with contextlib.suppress(NotNegatable):
                tokens.add(try_negate_name(token))
    valid_arities = signature.FUNCTION_ARITIES | signature.RELATION_ARITIES
    for c in tokens:
        arity = signature.get_arity(c)
        if arity in valid_arities:
            symbols.setdefault(signature.get_arity(c), []).append(c)
    for val in list(symbols.values()):
        val.sort()
    return symbols


def write_programs(rules):
    sequents = set(rules)
    programs = []
    write_full_programs(programs, sequents)
    write_event_programs(programs, sequents)
    return programs


def write_symbols(rules, facts):
    sequents = set(rules) if rules else set()
    facts = set(facts) if facts else set()
    symbols = get_symbols_used_in(sequents, facts)
    symbols = [
        (arity, name)
        for arity, names in list(symbols.items())
        if (arity in signature.FUNCTION_ARITIES or arity in signature.RELATION_ARITIES)
        for name in names
        if name != "EQUAL"
    ]
    symbols.sort(
        key=lambda arity_name: (signature.arity_sort(arity_name[0]), arity_name[1])
    )
    return symbols
