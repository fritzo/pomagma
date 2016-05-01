#pragma once

#include "util.hpp"
#include <pomagma/atlas/sampler.hpp>

namespace pomagma {

class Carrier;
class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

class Sampler::Policy : noncopyable {
   public:
    Carrier& carrier;

    explicit Policy(Carrier& c) : carrier(c) {}

    Ob sample(const NullaryFunction& fun);
    Ob sample(const InjectiveFunction& fun, Ob key);
    Ob sample(const BinaryFunction& fun, Ob lhs, Ob rhs);
    Ob sample(const SymmetricFunction& fun, Ob lhs, Ob rhs);
};

}  // namespace pomagma
