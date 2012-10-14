#pragma once

#include "util.hpp"

// The Scheduler guarantees:
// - never to execute a strict while any other task is being executed
//   (strict tasks are: MergeTask, SampleTask)
// - to execute a MergeTask as soon as all previous tasks complete
// - never to execute a SampleTask when dep obs exist
//   (ie until all scheduled MergeTasks have been executed)
// - while executing an MergeTask(dep), to discard all tasks touching dep
// TODO work out insert/remove/merge constraints
// - ??? do not remove a rep ob without removing its deps

namespace pomagma
{

class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;


struct SampleTask
{
};

struct MergeTask
{
    Ob dep;

    MergeTask () {}
    MergeTask (Ob d) : dep(d) {}
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

struct DiffuseTask
{
    //Ob ob;
    //DiffuseTask () {}
    //DiffuseTask (Ob ob) : type(ob) {}
};

struct CleanupTask
{
    //size_t type;
    //CleanupTask () {}
    //CleanupTask (size_t t) : type(t) {}
};


class CyclicQueue
{
    std::atomic<uint_fast64_t> m_state;
public:
    CyclicQueue () : m_state(0) {}

    uint_fast64_t pop_modulo (uint_fast64_t modulus)
    {
        uint_fast64_t state = m_state.load();
        uint_fast64_t next;
        do {
            next = state + 1 % modulus;
        } while (not m_state.compare_exchange_weak(state, next));
        return next;
    }
};

/*
// TODO move this to sampler.cpp for execute (const DiffuseTask &)
template<class Task>
class CyclicObQueue
{
    CyclicQueue m_queue;

public:

    void execute ()
    {
        // TODO move this logic to execute(const DiffuseTask &) in sampler.cpp
        Ob ob;
        do {
            ob = 1 + m_queue.pop_modulo(carrier.item_dim());
        } while (not carrier.support().contains(ob));
        execute(Task(ob));
    }
};
*/

// These are defined by the Scheduler and called by the user
void schedule (const MergeTask & task);
void schedule (const ExistsTask & task);
void schedule (const PositiveOrderTask & task);
void schedule (const NegativeOrderTask & task);
void schedule (const NullaryFunctionTask & task);
void schedule (const InjectiveFunctionTask & task);
void schedule (const BinaryFunctionTask & task);
void schedule (const SymmetricFunctionTask & task);
// Other tasks are run continuously, not scheduled:
// SampleTask, CleanupTask, DiffuseTask

// These are defined by the user and called by the Scheduler
void execute (const MergeTask & task);
void execute (const ExistsTask & task);
void execute (const PositiveOrderTask & task);
void execute (const NegativeOrderTask & task);
void execute (const NullaryFunctionTask & task);
void execute (const InjectiveFunctionTask & task);
void execute (const BinaryFunctionTask & task);
void execute (const SymmetricFunctionTask & task);
void execute (const CleanupTask & task);
void execute (const DiffuseTask & task);
Ob execute (const SampleTask & task);


namespace Scheduler
{

bool is_alive ();
void set_thread_counts (
        size_t worker_threads,
        size_t cleanup_threads,
        size_t diffuse_threads);
void start ();
void stop ();

} // namespace Scheduler


} // namespace pomagma
