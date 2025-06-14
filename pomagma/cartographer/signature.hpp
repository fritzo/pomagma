#pragma once

#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/atlas/signature.hpp>
#include <pomagma/util/sequential/dense_set.hpp>

namespace pomagma {

/// Extend destin to source's language
void extend(Signature& destin, const Signature& source);

/// Return subset of destin which is definable in source's language
DenseSet restricted(const Signature& destin, const Signature& source);

}  // namespace pomagma
