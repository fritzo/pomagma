#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/platform/signature.hpp>
#include <pomagma/platform/sequential/dense_set.hpp>

namespace pomagma
{

/// Extend destin to source's language
void extend (Signature & destin, const Signature & source);

/// Return subset of destin which is definable in source's language
DenseSet restricted (const Signature & destin, const Signature & source);

} // namespace pomagma
