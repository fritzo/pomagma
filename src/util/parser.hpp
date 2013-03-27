#pragma once

// Assumes the following are defined:
// Ob
// Carrier
// NullaryFunction
// InjectiveFunction
// BinaryFunction
// SymmetricFunction
#include "util.hpp"

namespace pomagma
{

class Signature;

class Parser : noncopyable
{
    Signature & m_signature;

public:

    Parser (Signature & signature);

    class Policy; // implementation-specific
    Ob parse_insert (std::istringstream & stream, Policy & policy) const;
};

} // namespace pomagma
