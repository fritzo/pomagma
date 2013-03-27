#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/parser.hpp>

namespace pomagma
{

struct Parser::Policy : noncopyable
{
    Carrier & carrier;

    Policy (Carrier & c) : carrier(c) {}

    Ob check_insert (const NullaryFunction * fun) const
    {
        Ob val = fun->find();
        if (not val) {
            val = carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(val);
        }
        return val;
    }

    Ob check_insert (const InjectiveFunction * fun, Ob key) const
    {
        Ob val = fun->find(key);
        if (not val) {
            val = carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(key, val);
        }
        return val;
    }

    Ob check_insert (
            const BinaryFunction * fun,
            Ob lhs,
            Ob rhs) const
    {
        Ob val = fun->find(lhs, rhs);
        if (not val) {
            val = carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(lhs, rhs, val);
        }
        return val;
    }

    Ob check_insert (
            const SymmetricFunction * fun,
            Ob lhs,
            Ob rhs) const
    {
        Ob val = fun->find(lhs, rhs);
        if (not val) {
            val = carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(lhs, rhs, val);
        }
        return val;
    }
};

} // namespace pomagma
