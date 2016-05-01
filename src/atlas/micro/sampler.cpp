#include "sampler.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/atlas/sampler_impl.hpp>

namespace pomagma {

inline Ob Sampler::Policy::sample(const NullaryFunction& fun) {
    if (Ob val = fun.find()) {
        return carrier.find(val);
    }
    if (Ob val = carrier.try_insert()) {
        fun.insert(val);
        throw ObInsertedException(val);
    }
    throw InsertionFailedException();
}

inline Ob Sampler::Policy::sample(const InjectiveFunction& fun, Ob key) {
    if (Ob val = fun.find(key)) {
        return carrier.find(val);
    }
    if (Ob val = carrier.try_insert()) {
        fun.insert(key, val);
        throw ObInsertedException(val);
    }
    throw InsertionFailedException();
}

inline Ob Sampler::Policy::sample(const BinaryFunction& fun, Ob lhs, Ob rhs) {
    if (Ob val = fun.find(lhs, rhs)) {
        return carrier.find(val);
    }
    if (Ob val = carrier.try_insert()) {
        fun.insert(lhs, rhs, val);
        throw ObInsertedException(val);
    }
    throw InsertionFailedException();
}

inline Ob Sampler::Policy::sample(const SymmetricFunction& fun, Ob lhs,
                                  Ob rhs) {
    if (Ob val = fun.find(lhs, rhs)) {
        return carrier.find(val);
    }
    if (Ob val = carrier.try_insert()) {
        fun.insert(lhs, rhs, val);
        throw ObInsertedException(val);
    }
    throw InsertionFailedException();
}

}  // namespace pomagma
