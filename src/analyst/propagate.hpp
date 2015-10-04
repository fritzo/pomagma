#pragma once

#include <pomagma/analyst/intervals.hpp>
#include <pomagma/util/trool.hpp>
#include <vector>
#include <memory>

namespace pomagma {
namespace propagate {

using ::pomagma::intervals::Approximator;

// These correspond to ExprParser cases
enum Arity
{
    NULLARY_FUNCTION,
    INJECTIVE_FUNCTION,
    BINARY_FUNCTION,
    SYMMETRIC_FUNCTION,
    UNARY_RELATION,
    BINARY_RELATION,
    EQUAL,
    HOLE,
    VAR
};

struct Expr
{
    const Arity arity;
    const std::string name;
    const std::shared_ptr<Expr> args[2];
};

struct Theory
{
    const std::vector<std::shared_ptr<Expr>> facts;
    const std::vector<const Expr *> exprs; // a flattened copy of facts
};

Theory parse_theory (
    Signature & signature,
    const std::vector<std::string> & polish_facts,
    std::vector<std::string> & error_log);

// This fast best-effort solver immediately returns a partial solution, and
// guarantees to eventually return a complete solution upon repeated calls.
Trool lazy_validate (const Theory & theory, Approximator & approximator);

} // namespace propagate
} // namespace pomagma 
