#ifndef POMAGMA_SCHEDULER_HPP
#define POMAGMA_SCHEDULER_HPP

#include "util.hpp"

namespace pomagma
{

class NullaryFunction;
class UnaryFunction;
class BinaryFunction;
class SymmetricFunction;


struct MergeTask
{
    oid_t dep;

    MergeTask () {}
    MergeTask (oid_t d) : dep(d) {}
};

struct CleanupTask
{
    size_t type;

    CleanupTask () {}
    CleanupTask (size_t t) : type(t) {}

    bool references (oid_t) const { return false; }
};

struct PositiveOrderTask
{
    oid_t lhs;
    oid_t rhs;

    PositiveOrderTask () {}
    PositiveOrderTask (oid_t l, oid_t r) : lhs(l), rhs(r) {}

    bool references (oid_t dep) const { return lhs == dep or rhs == dep; }
};

struct NegativeOrderTask
{
    oid_t lhs;
    oid_t rhs;

    NegativeOrderTask () {}
    NegativeOrderTask (oid_t l, oid_t r) : lhs(l), rhs(r) {}

    bool references (oid_t dep) const { return lhs == dep or rhs == dep; }
};

struct NullaryFunctionTask
{
    NullaryFunction * fun;

    NullaryFunctionTask () {}
    NullaryFunctionTask (NullaryFunction & f) : fun(&f) {}

    bool references (oid_t) const { return false; }
};

struct UnaryFunctionTask
{
    UnaryFunction * fun;
    oid_t arg;

    UnaryFunctionTask () {}
    UnaryFunctionTask (UnaryFunction & f, oid_t a) : fun(&f), arg(a) {}

    bool references (oid_t dep) const { return arg == dep; }
};

struct BinaryFunctionTask
{
    BinaryFunction * fun;
    oid_t lhs;
    oid_t rhs;

    BinaryFunctionTask () {}
    BinaryFunctionTask (BinaryFunction & f, oid_t l, oid_t r)
        : fun(&f), lhs(l), rhs(r)
    {}

    bool references (oid_t dep) const { return lhs == dep or rhs == dep; }
};

struct SymmetricFunctionTask
{
    SymmetricFunction * fun;
    oid_t lhs;
    oid_t rhs;

    SymmetricFunctionTask () {}
    SymmetricFunctionTask (SymmetricFunction & f, oid_t l, oid_t r)
        : fun(&f), lhs(l), rhs(r)
    {}

    bool references (oid_t dep) const { return lhs == dep or rhs == dep; }
};


// The Scheduler guarantees:
// - never to execute an MergeTask while any other task is being executed
// - to execute an MergeTask as soon as all previous tasks complete
// - while executing an MergeTask(dep), to discard all tasks touching dep

// These are defined by the Scheduler and called by the user
void schedule (const MergeTask & task);
void schedule (const CleanupTask & task);
void schedule (const PositiveOrderTask & task);
void schedule (const NegativeOrderTask & task);
void schedule (const NullaryFunctionTask & task);
void schedule (const UnaryFunctionTask & task);
void schedule (const BinaryFunctionTask & task);
void schedule (const SymmetricFunctionTask & task);

// These are defined by the user and called by the Scheduler
void execute (const MergeTask & task);
void execute (const CleanupTask & task);
void execute (const PositiveOrderTask & task);
void execute (const NegativeOrderTask & task);
void execute (const NullaryFunctionTask & task);
void execute (const UnaryFunctionTask & task);
void execute (const BinaryFunctionTask & task);
void execute (const SymmetricFunctionTask & task);


namespace Scheduler
{

void start (size_t thread_count);
void stopall ();

} // namespace Scheduler


} // namespace pomagma

#endif // POMAGMA_SCHEDULER_HPP
