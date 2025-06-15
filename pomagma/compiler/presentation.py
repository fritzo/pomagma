import pomagma.compiler.syntax as proto
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.util import cached, methodof


@methodof(proto.Expression)
def pythonize_expr(proto_expr):
    return parse_string_to_expr(proto_expr.polish)


@methodof(proto.Sequent)
def pythonize_sequent(proto_sequent):
    antecedents = list(map(pythonize_expr, proto_sequent.antecedents))
    succedents = list(map(pythonize_expr, proto_sequent.succedents))
    return Sequent(antecedents, succedents)


@methodof(proto.Theory)
def pythonize_theory(proto_theory):
    return {
        "facts": set(map(pythonize_expr, proto_theory.facts)),
        "rules": set(map(pythonize_sequent, proto_theory.rules)),
    }


@cached
@methodof(proto.Theory, proto.Theory)
def entails(lhs, rhs):
    raise NotImplementedError
