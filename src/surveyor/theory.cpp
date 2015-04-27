#include "theory.hpp"
#include <pomagma/microstructure/sampler.hpp>
#include <pomagma/microstructure/structure_impl.hpp>
#include <pomagma/microstructure/scheduler.hpp>
#include "insert_parser.hpp"
#include "cleanup.hpp"
#include "vm.hpp"

namespace pomagma
{

//----------------------------------------------------------------------------
// signature

static Structure structure;
static Signature & signature = structure.signature();
static Sampler sampler(signature);
static vm::Agenda agenda;

void load_structure (const std::string & filename) { structure.load(filename); }
void dump_structure (const std::string & filename) { structure.dump(filename); }
void load_language (const std::string & filename) { sampler.load(filename); }
void load_programs (const std::string & filename)
{
    agenda.load(signature);
    vm::Parser parser(signature);
    auto listings = parser.parse_file(filename);
    for (const auto & listing : listings) {
        agenda.add_listing(listing);
    }
    agenda.log_stats();
    agenda.optimize_listings();
    agenda.log_stats();
    Cleanup::init(agenda.cleanup_task_count());
    CleanupProfiler::init(agenda.cleanup_type_count());
}

static void schedule_merge (Ob dep) { schedule(MergeTask(dep)); }
static void schedule_exists (Ob ob) { schedule(ExistsTask(ob)); }
static void schedule_less (Ob lhs, Ob rhs)
{
    schedule(PositiveOrderTask(lhs, rhs));
}
static void schedule_nless (Ob lhs, Ob rhs)
{
    schedule(NegativeOrderTask(lhs, rhs));
}

static Carrier carrier(
    getenv_default("POMAGMA_SIZE", DEFAULT_ITEM_DIM),
    schedule_exists,
    schedule_merge);

static BinaryRelation LESS(carrier, schedule_less);
static BinaryRelation NLESS(carrier, schedule_nless);

void load_signature (const std::string & filename)
{
    signature.declare(carrier);
    signature.declare("LESS", LESS);
    signature.declare("NLESS", NLESS);

    std::ifstream infile(filename, std::ifstream::in | std::ifstream::binary);
    POMAGMA_ASSERT(infile.is_open(), "failed to open file: " << filename)

    std::string line;
    std::string arity;
    std::string name;
    while (std::getline(infile, line)) {
        if (line.empty() or line[0] == '#') {
            continue;
        }
        std::istringstream stream(line);
        stream >> arity >> name;

        if (arity == "UnaryRelation") {
            if (not signature.unary_relation(name)) {
                signature.declare(name, * new UnaryRelation(carrier));
            }
        } else if (arity == "BinaryRelation") {
            if (not signature.binary_relation(name)) {
                signature.declare(name, * new BinaryRelation(carrier));
            }
        } else if (arity == "NullaryFunction") {
            if (not signature.nullary_function(name)) {
                signature.declare(name, * new NullaryFunction(carrier));
            }
        } else if (arity == "InjectiveFunction") {
            if (not signature.injective_function(name)) {
                signature.declare(name, * new InjectiveFunction(carrier));
            }
        } else if (arity == "BinaryFunction") {
            if (not signature.binary_function(name)) {
                signature.declare(name, * new BinaryFunction(carrier));
            }
        } else if (arity == "SymmetricFunction") {
            if (not signature.symmetric_function(name)) {
                signature.declare(name, * new SymmetricFunction(carrier));
            }
        } else {
            POMAGMA_ERROR("unknown arity: " << arity);
        }
    }
}

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

void log_profile_stats ()
{
    CleanupProfiler::log_stats();
}

void log_stats ()
{
    structure.log_stats();
    sampler.log_stats();
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
    POMAGMA_DEBUG("executing sample task");
    Sampler::Policy policy(carrier);
    sampler.try_insert_random(rng, policy);
}

//----------------------------------------------------------------------------
// merge tasks

void execute (const MergeTask & task)
{
    const Ob dep = task.dep;
    const Ob rep = carrier.find(dep);
    POMAGMA_DEBUG("merging: " << dep << " = " << rep);
    POMAGMA_ASSERT(dep > rep, "ill-formed merge: " << dep << ", " << rep);
    bool invalid = NLESS.find(dep, rep) or NLESS.find(rep, dep);
    POMAGMA_ASSERT(not invalid, "invalid merge: " << dep << ", " << rep);
    std::vector<std::thread> threads;

    // expensive merges in other threads
    for (const auto & pair : signature.binary_relations()) {
        threads.push_back(std::thread(
            &BinaryRelation::unsafe_merge,
            pair.second,
            dep));
    }
    for (const auto & pair : signature.binary_functions()) {
        threads.push_back(std::thread(
            &BinaryFunction::unsafe_merge,
            pair.second,
            dep));
    }
    for (const auto & pair : signature.symmetric_functions()) {
        threads.push_back(std::thread(
            &SymmetricFunction::unsafe_merge,
            pair.second,
            dep));
    }

    // cheap merges in this thread
    for (const auto & pair : signature.unary_relations()) {
        pair.second->unsafe_merge(dep);
    }
    for (const auto & pair : signature.nullary_functions()) {
        pair.second->unsafe_merge(dep);
    }
    for (const auto & pair : signature.injective_functions()) {
        pair.second->unsafe_merge(dep);
    }

    for (auto & thread : threads) {
        thread.join();
    }
    carrier.unsafe_remove(dep);
}

//----------------------------------------------------------------------------
// assume tasks

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

void execute (const AssumeTask & task)
{
    POMAGMA_DEBUG("assume " << task.expression);

    InsertParser parser(signature);
    parser.begin(task.expression);
    std::string type = parser.parse_token();

    if (type == "EQUAL") {
        Ob lhs = parser.parse_term();
        Ob rhs = parser.parse_term();
        parser.end();
        carrier.ensure_equal(lhs, rhs);
    } else if (auto * rel = signature.unary_relation(type)) {
        Ob key = parser.parse_term();
        parser.end();
        rel->insert(key);
    } else if (auto * rel = signature.binary_relation(type)) {
        Ob lhs = parser.parse_term();
        Ob rhs = parser.parse_term();
        parser.end();
        rel->insert(lhs, rhs);
    } else {
        POMAGMA_ERROR("bad relation type: " << type);
    }
}

//----------------------------------------------------------------------------
// cleanup & event tasks

void execute (const ExistsTask & task)
{
    agenda.execute(task.ob);
}

void execute (const NullaryFunctionTask & task)
{
    agenda.execute(task.ptr);
}

void execute (const InjectiveFunctionTask & task)
{
    agenda.execute(task.ptr, task.arg);
}

void execute (const BinaryFunctionTask & task)
{
    agenda.execute(task.ptr, task.lhs, task.rhs);
}

void execute (const SymmetricFunctionTask & task)
{
    agenda.execute(task.ptr, task.lhs, task.rhs);
}

void execute (const UnaryRelationTask & task)
{
    agenda.execute(task.ptr, task.arg);
}

void execute (const PositiveOrderTask & task)
{
    agenda.execute(&LESS, task.lhs, task.rhs);
}

void execute (const NegativeOrderTask & task)
{
    agenda.execute(&NLESS, task.lhs, task.rhs);
}

void execute (const CleanupTask & task)
{
    agenda.execute_cleanup(task.type);
}

} // namespace pomagma
