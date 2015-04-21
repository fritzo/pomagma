#pragma once
// WARNING this should only be linked to once

#include <pomagma/microstructure/util.hpp>
#include <pomagma/microstructure/sampler.hpp>
#include <pomagma/microstructure/structure_impl.hpp>
#include <pomagma/microstructure/scheduler.hpp>
#include "insert_parser.hpp"
#include "vm.hpp"
#include "cleanup.hpp"
#include <atomic>
#include <thread>
#include <vector>

namespace pomagma
{

//----------------------------------------------------------------------------
// signature

Structure structure;
Signature & signature = structure.signature();
Sampler sampler(signature);

void load_structure (const std::string & filename) { structure.load(filename); }
void dump_structure (const std::string & filename) { structure.dump(filename); }
void load_language (const std::string & filename) { sampler.load(filename); }

void schedule_merge (Ob dep) { schedule(MergeTask(dep)); }
void schedule_exists (Ob ob) { schedule(ExistsTask(ob)); }
void schedule_less (Ob lhs, Ob rhs) { schedule(PositiveOrderTask(lhs, rhs)); }
void schedule_nless (Ob lhs, Ob rhs) { schedule(NegativeOrderTask(lhs, rhs)); }
void schedule_unary_relation (const UnaryRelation * rel, Ob arg)
{
    schedule(UnaryRelationTask(*rel, arg));
}
void schedule_nullary_function (const NullaryFunction * fun)
{
    schedule(NullaryFunctionTask(*fun));
}
void schedule_injective_function (const InjectiveFunction * fun, Ob arg)
{
    schedule(InjectiveFunctionTask(*fun, arg));
}
void schedule_binary_function (const BinaryFunction * fun, Ob lhs, Ob rhs)
{
    schedule(BinaryFunctionTask(*fun, lhs, rhs));
}
void schedule_symmetric_function (const SymmetricFunction * fun, Ob lhs, Ob rhs)
{
    schedule(SymmetricFunctionTask(*fun, lhs, rhs));
}

Carrier carrier(
    getenv_default("POMAGMA_SIZE", DEFAULT_ITEM_DIM),
    schedule_exists,
    schedule_merge);

BinaryRelation LESS(carrier, schedule_less);
BinaryRelation NLESS(carrier, schedule_nless);

//----------------------------------------------------------------------------
// validation

void validate_consistent ()
{
    structure.validate_consistent();
}

void validate_all ()
{
    structure.validate();
    sampler.validate();
}

//----------------------------------------------------------------------------
// logging

void log_stats ()
{
    structure.log_stats();
    sampler.log_stats();
}

//----------------------------------------------------------------------------
// basic ensurers

inline void ensure_equal (Ob lhs, Ob rhs)
{
    carrier.ensure_equal(lhs, rhs);
}

inline void ensure_less (Ob lhs, Ob rhs)
{
    LESS.insert(lhs, rhs);
}

inline void ensure_nless (Ob lhs, Ob rhs)
{
    NLESS.insert(lhs, rhs);
}

//----------------------------------------------------------------------------
// expression parsing

void assume_core_facts (const char * theory_file)
{
    std::ifstream file(theory_file);
    POMAGMA_ASSERT(file, "failed to open " << theory_file);

    std::string expression;
    while (getline(file, expression)) {
        if (not expression.empty() and expression[0] != '#') {
            schedule(AssumeTask(expression));
        }
    }
}

//----------------------------------------------------------------------------
// sample tasks

void insert_nullary_functions ()
{
    const auto & functions = signature.nullary_functions();
    POMAGMA_INFO("Inserting " << functions.size() << " nullary functions");

    for (auto pair : functions) {
        NullaryFunction * fun = pair.second;
        if (not fun->find()) {
            Ob val = carrier.try_insert();
            POMAGMA_ASSERT(val, "no space to insert nullary functions");
            fun->insert(val);
        }
    }
}

bool sample_tasks_try_pop (SampleTask &)
{
    return carrier.item_count() < carrier.item_dim();
}

void execute (const SampleTask &, rng_t & rng)
{
    Sampler::Policy policy(carrier);
    sampler.try_insert_random(rng, policy);
}

} // namespace pomagma
