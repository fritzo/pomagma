#pragma once

#include "util.hpp"
#include <pomagma/util/parser.hpp>

namespace pomagma
{

class Carrier;
class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

struct Parser::Policy : noncopyable
{
    Carrier & carrier;

    Policy (Carrier & c) : carrier(c) {}

    Ob check_insert (const NullaryFunction * fun) const;
    Ob check_insert (const InjectiveFunction * fun, Ob key) const;
    Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs) const;
    Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs) const;
};

} // namespace pomagma
