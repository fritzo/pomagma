#include "theory.hpp"
#include "vm.hpp"

namespace pomagma
{

vm::Agenda agenda;

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

void load_programs (const std::string & filename)
{
    agenda.load(signature);
    vm::Parser parser(signature);
    auto listings = parser.parse_file(filename);
    for (const auto & listing : listings) {
        agenda.add_listing(listing);
    }
    CleanupProfiler::init(agenda.cleanup_type_count());
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
// cleanup tasks

std::atomic<unsigned long> g_cleanup_type(0);
std::atomic<unsigned long> g_cleanup_remaining(0);

void cleanup_tasks_push_all ()
{
    g_cleanup_remaining.store(agenda.cleanup_task_count());
}

bool cleanup_tasks_try_pop (CleanupTask & task)
{
    unsigned long remaining = 1;
    while (not g_cleanup_remaining.compare_exchange_weak(
        remaining, remaining - 1))
    {
        if (remaining == 0) {
            CleanupProfiler::cleanup();
            return false;
        }
    }

    const unsigned long type_count = agenda.cleanup_task_count();
    unsigned long type = 0;
    while (not g_cleanup_type.compare_exchange_weak(
        type, (type + 1) % type_count))
    {
    }

    task.type = type;
    return true;
}

void execute (const CleanupTask & task)
{
    agenda.execute_cleanup(task.type);
}

//----------------------------------------------------------------------------
// event tasks

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

} // namespace pomagma
