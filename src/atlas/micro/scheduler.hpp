#pragma once

#include "util.hpp"

// The Scheduler guarantees:
// - never to execute a MergeTask while any other task is being executed
// - to execute a MergeTask as soon as all previous tasks complete
// - while executing an MergeTask(dep), to discard all tasks touching dep
// TODO work out insert/merge constraints
// - ??? do not remove a rep ob without removing its deps

namespace pomagma {

const size_t DEFAULT_THREAD_COUNT = 1;

class UnaryRelation;
class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

struct MergeTask {
    Ob dep;

    MergeTask() {}
    explicit MergeTask(Ob d) : dep(d) {}
};

struct ExistsTask {
    Ob ob;

    ExistsTask() {}
    explicit ExistsTask(Ob o) : ob(o) {}

    bool references(Ob dep) const { return ob == dep; }
};

struct PositiveOrderTask {
    Ob lhs;
    Ob rhs;

    PositiveOrderTask() {}
    PositiveOrderTask(Ob l, Ob r) : lhs(l), rhs(r) {}

    bool references(Ob dep) const { return lhs == dep or rhs == dep; }
};

struct NegativeOrderTask {
    Ob lhs;
    Ob rhs;

    NegativeOrderTask() {}
    NegativeOrderTask(Ob l, Ob r) : lhs(l), rhs(r) {}

    bool references(Ob dep) const { return lhs == dep or rhs == dep; }
};

struct UnaryRelationTask {
    const UnaryRelation* ptr;
    Ob arg;

    UnaryRelationTask() {}
    UnaryRelationTask(const UnaryRelation& r, Ob a) : ptr(&r), arg(a) {}

    bool references(Ob dep) const { return arg == dep; }
};

struct NullaryFunctionTask {
    const NullaryFunction* ptr;

    NullaryFunctionTask() {}
    explicit NullaryFunctionTask(const NullaryFunction& f) : ptr(&f) {}

    bool references(Ob) const { return false; }
};

struct InjectiveFunctionTask {
    const InjectiveFunction* ptr;
    Ob arg;

    InjectiveFunctionTask() {}
    InjectiveFunctionTask(const InjectiveFunction& f, Ob a) : ptr(&f), arg(a) {}

    bool references(Ob dep) const { return arg == dep; }
};

struct BinaryFunctionTask {
    const BinaryFunction* ptr;
    Ob lhs;
    Ob rhs;

    BinaryFunctionTask() {}
    BinaryFunctionTask(const BinaryFunction& f, Ob l, Ob r)
        : ptr(&f), lhs(l), rhs(r) {}

    bool references(Ob dep) const { return lhs == dep or rhs == dep; }
};

struct SymmetricFunctionTask {
    const SymmetricFunction* ptr;
    Ob lhs;
    Ob rhs;

    SymmetricFunctionTask() {}
    SymmetricFunctionTask(const SymmetricFunction& f, Ob l, Ob r)
        : ptr(&f), lhs(l), rhs(r) {}

    bool references(Ob dep) const { return lhs == dep or rhs == dep; }
};

struct AssumeTask {
    std::string expression;

    AssumeTask() {}
    explicit AssumeTask(const std::string& e) : expression(e) {}

    bool references(Ob) = delete;
};

struct CleanupTask {
    unsigned long type;

    CleanupTask() {}
    explicit CleanupTask(unsigned long t) : type(t) {}
};

struct SampleTask {};

// These are defined by the Scheduler and called by the user
void schedule(const MergeTask& task);
void schedule(const ExistsTask& task);
void schedule(const PositiveOrderTask& task);
void schedule(const NegativeOrderTask& task);
void schedule(const UnaryRelationTask& task);
void schedule(const NullaryFunctionTask& task);
void schedule(const InjectiveFunctionTask& task);
void schedule(const BinaryFunctionTask& task);
void schedule(const SymmetricFunctionTask& task);
void schedule(const AssumeTask& task);
// Other tasks are run continuously, not scheduled:
// SampleTask, CleanupTask

// These are defined by the user and called by the Scheduler
void execute(const MergeTask& task);
void execute(const ExistsTask& task);
void execute(const PositiveOrderTask& task);
void execute(const NegativeOrderTask& task);
void execute(const UnaryRelationTask& task);
void execute(const NullaryFunctionTask& task);
void execute(const InjectiveFunctionTask& task);
void execute(const BinaryFunctionTask& task);
void execute(const SymmetricFunctionTask& task);
void execute(const AssumeTask& task);
void execute(const CleanupTask& task);
void execute(const SampleTask& task, rng_t& rng);

void insert_nullary_functions();
void assume_core_facts(const char* theory_file);
bool sample_tasks_try_pop(SampleTask& task);

namespace Cleanup {
void init(size_t type_count);
}

namespace Scheduler {

void set_thread_count(size_t worker_count = 0);

// blocking api, requires access from single thread
void initialize(const char* theory_file = nullptr);
void survey();
void survey_until_deadline(const char* theory_file = nullptr);

}  // namespace Scheduler

}  // namespace pomagma
