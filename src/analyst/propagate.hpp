#pragma once

#include <pomagma/analyst/intervals.hpp>
#include <memory>
#include <vector>

namespace pomagma {
namespace propagate {

using intervals::Parity;
using intervals::Direction;

enum Arity
{
    NULLARY_FUNCTION,
    INJECTIVE_FUNCTION,
    BINARY_FUNCTION,
    SYMMETRIC_FUNCTION,
    UNARY_RELATION,
    BINARY_RELATION,
    VARIABLE,
    HOLE
};

// These are cons-hashed to ensure uniqueness.
struct Term
{
    const Arity arity;
    const string name;
    const std::unique_ptr<Term> args[2];
};

struct Corpus
{
    const std::vector<uniqe_ptr<Term>> lines;
};

// TODO define parse : ... -> Corpus, which creates cons-hashed terms

struct Constraint
{
    const Term * term;
    Direction direction;
};

struct Problem
{
    const std::unique_ptr<Corpus> corpus;
    const std::unordered_map<const Term *, std::vector<Constraint>> constraints;
};

Problem formulate (std::unique_ptr<Corpus> corpus);

typedef intervals::Approximation State;

struct Solution
{
    const std::unique_ptr<Corpus> corpus;
    const std::unordered_map<const Term *, State> states;
};

// This fast best-effort solver immediately returns a partial solution, and
// guarantees to eventually return a complete solution upon repeated calls.
Solution solve (
    const Problem & problem,
    intervals::Approximator & approximator);

bool is_pending (const Solution & solution);

} // namespace propagate
} // namespace pomagma 
