#pragma once

#include <pomagma/analyst/intervals.hpp>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <memory>

namespace pomagma {
namespace propagate {

using intervals::Parity;

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
    const std::string name;
    const std::shared_ptr<Term> args[2];
};

struct Corpus
{
    const std::vector<std::shared_ptr<Term>> lines;
};

// TODO define parse : ... -> Corpus, which creates cons-hashed terms

struct Problem
{
    const std::shared_ptr<Corpus> corpus;
    const std::unordered_set<const Term *> constraints;
};

Problem formulate (std::shared_ptr<Corpus> corpus);

typedef intervals::Approximation State;

struct Solution
{
    const std::shared_ptr<Corpus> corpus;
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
