#pragma once

#include "util.hpp"

// The Scheduler guarantees:
// - never to execute a MergeTask while any other task is being executed
// - to execute a MergeTask as soon as all previous tasks complete
// - while executing an MergeTask(dep), to discard all tasks touching dep
// TODO work out insert/remove/merge constraints

namespace pomagma
{

class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

struct ResizeTask
{
};

struct MergeTask
{
    Ob dep;

    MergeTask () {}
    MergeTask (Ob d) : dep(d) {}
};

struct CleanupTask
{
    size_t type;

    CleanupTask () {}
    CleanupTask (size_t t) : type(t) {}

    bool references (Ob) const { return false; }
};

struct ExistsTask
{
    Ob ob;

    ExistsTask () {}
    ExistsTask (Ob o) : ob(o) {}

    bool references (Ob dep) const { return ob == dep; }
};

struct PositiveOrderTask
{
    Ob lhs;
    Ob rhs;

    PositiveOrderTask () {}
    PositiveOrderTask (Ob l, Ob r) : lhs(l), rhs(r) {}

    bool references (Ob dep) const { return lhs == dep or rhs == dep; }
};

struct NegativeOrderTask
{
    Ob lhs;
    Ob rhs;

    NegativeOrderTask () {}
    NegativeOrderTask (Ob l, Ob r) : lhs(l), rhs(r) {}

    bool references (Ob dep) const { return lhs == dep or rhs == dep; }
};

struct NullaryFunctionTask
{
    const NullaryFunction * fun;

    NullaryFunctionTask () {}
    NullaryFunctionTask (const NullaryFunction & f) : fun(&f) {}

    bool references (Ob) const { return false; }
};

struct InjectiveFunctionTask
{
    const InjectiveFunction * fun;
    Ob arg;

    InjectiveFunctionTask () {}
    InjectiveFunctionTask (const InjectiveFunction & f, Ob a)
        : fun(&f), arg(a)
    {}

    bool references (Ob dep) const { return arg == dep; }
};

struct BinaryFunctionTask
{
    const BinaryFunction * fun;
    Ob lhs;
    Ob rhs;

    BinaryFunctionTask () {}
    BinaryFunctionTask (const BinaryFunction & f, Ob l, Ob r)
        : fun(&f), lhs(l), rhs(r)
    {}

    bool references (Ob dep) const { return lhs == dep or rhs == dep; }
};

struct SymmetricFunctionTask
{
    const SymmetricFunction * fun;
    Ob lhs;
    Ob rhs;

    SymmetricFunctionTask () {}
    SymmetricFunctionTask (const SymmetricFunction & f, Ob l, Ob r)
        : fun(&f), lhs(l), rhs(r)
    {}

    bool references (Ob dep) const { return lhs == dep or rhs == dep; }
};


// These are defined by the Scheduler and called by the user
void schedule (const MergeTask & task);
void schedule (const CleanupTask & task);
void schedule (const ExistsTask & task);
void schedule (const PositiveOrderTask & task);
void schedule (const NegativeOrderTask & task);
void schedule (const NullaryFunctionTask & task);
void schedule (const InjectiveFunctionTask & task);
void schedule (const BinaryFunctionTask & task);
void schedule (const SymmetricFunctionTask & task);

// These are defined by the user and called by the Scheduler
void execute (const MergeTask & task);
void execute (const CleanupTask & task);
void execute (const ExistsTask & task);
void execute (const PositiveOrderTask & task);
void execute (const NegativeOrderTask & task);
void execute (const NullaryFunctionTask & task);
void execute (const InjectiveFunctionTask & task);
void execute (const BinaryFunctionTask & task);
void execute (const SymmetricFunctionTask & task);


namespace Scheduler
{

void start (size_t thread_count);
void stopall ();

} // namespace Scheduler


} // namespace pomagma
