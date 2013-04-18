#pragma once

#include "util.hpp"
#include <pomagma/util/sampler.hpp>

namespace pomagma
{

class Carrier;
class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

struct Sampler::Policy : noncopyable
{
    Carrier & carrier;

    Policy (Carrier & c) : carrier(c) {}

    Ob sample (const NullaryFunction & fun);
    Ob sample (const InjectiveFunction & fun, Ob key);
    Ob sample (const BinaryFunction & fun, Ob lhs, Ob rhs);
    Ob sample (const SymmetricFunction & fun, Ob lhs, Ob rhs);
};

} // namespace pomagma
