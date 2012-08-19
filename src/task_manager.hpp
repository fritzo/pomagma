#ifndef POMAGMA_TASK_MANAGER_HPP
#define POMAGMA_TASK_MANAGER_HPP

#include "util.hpp"

namespace pomagma
{

class NullaryFunction;
class UnaryFunction;
class BinaryFunction;
class SymmetricFunction;
class BinaryRelation;


struct EquationTask
{
    oid_t dep;
    oid_t rep;

    EquationTask () {}
    EquationTask (oid_t d, oid_t r) : dep(d), rep(r) {}

    bool operator== (const EquationTask & other) const
    {
        return dep == other.dep and rep == other.rep;
    }
};

struct NullaryFunctionTask
{
    NullaryFunction * fun;

    NullaryFunctionTask () {}
    NullaryFunctionTask (NullaryFunction * f) : fun(f) {}

    bool operator== (const NullaryFunctionTask & other) const
    {
        return fun == other.fun;
    }
};

struct UnaryFunctionTask
{
    UnaryFunction * fun;
    oid_t arg;

    UnaryFunctionTask () {}
    UnaryFunctionTask (UnaryFunction * f, oid_t a) : fun(f), arg(a) {}

    bool operator== (const UnaryFunctionTask & other) const
    {
        return fun == other.fun and arg == other.arg;
    }
};

struct BinaryFunctionTask
{
    BinaryFunction * fun;
    oid_t lhs;
    oid_t rhs;

    BinaryFunctionTask () {}
    BinaryFunctionTask (BinaryFunction * f, oid_t l, oid_t r)
        : fun(f), lhs(l), rhs(r)
    {}

    bool operator== (const BinaryFunctionTask & other) const
    {
        return fun == other.fun and lhs == other.lhs and rhs == other.rhs;
    }
};

struct SymmetricFunctionTask
{
    SymmetricFunction * fun;
    oid_t lhs;
    oid_t rhs;

    SymmetricFunctionTask () {}
    SymmetricFunctionTask (SymmetricFunction * f, oid_t l, oid_t r)
        : fun(f), lhs(l), rhs(r)
    {}

    bool operator== (const SymmetricFunctionTask & other) const
    {
        return fun == other.fun and lhs == other.lhs and rhs == other.rhs;
    }
};

struct PositiveRelationTask
{
    BinaryRelation * rel;
    oid_t lhs;
    oid_t rhs;

    PositiveRelationTask () {}
    PositiveRelationTask (BinaryRelation * p, oid_t l, oid_t r)
        : rel(p), lhs(l), rhs(r)
    {}

    bool operator== (const PositiveRelationTask & other) const
    {
        return rel == other.rel and lhs == other.lhs and rhs == other.rhs;
    }
};

struct NegativeRelationTask
{
    BinaryRelation * rel;
    oid_t lhs;
    oid_t rhs;

    NegativeRelationTask () {}
    NegativeRelationTask (BinaryRelation * n, oid_t l, oid_t r)
        : rel(n), lhs(l), rhs(r)
    {}

    bool operator== (const NegativeRelationTask & other) const
    {
        return rel == other.rel and lhs == other.lhs and rhs == other.rhs;
    }
};


// these are defined by the TaskManager and called by the user
void enqueue (const EquationTask & task);
void enqueue (const NullaryFunctionTask & task);
void enqueue (const UnaryFunctionTask & task);
void enqueue (const BinaryFunctionTask & task);
void enqueue (const SymmetricFunctionTask & task);
void enqueue (const PositiveRelationTask & task);
void enqueue (const NegativeRelationTask & task);


// these are defined by the user and called by the TaskManager
void execute (const EquationTask & task);
void execute (const NullaryFunctionTask & task);
void execute (const UnaryFunctionTask & task);
void execute (const BinaryFunctionTask & task);
void execute (const SymmetricFunctionTask & task);
void execute (const PositiveRelationTask & task);
void execute (const NegativeRelationTask & task);


namespace TaskManager
{

void start (size_t thread_count);
void stopall ();

} // namespace TaskManager


} // namespace pomagma

#endif // POMAGMA_TASK_MANAGER_HPP
