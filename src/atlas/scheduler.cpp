#include "scheduler.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/signature.hpp>
#include <unordered_set>
#include <deque>

namespace pomagma
{

class UniqueFifoQueue
{
    std::unordered_set<Ob> m_set;
    std::deque<Ob> m_queue;

public:

    void push (const Ob & ob)
    {
        bool inserted = m_set.insert(ob).second;
        if (inserted) {
            m_queue.push_back(ob);
        }
    }

    Ob pop ()
    {
        if (m_queue.empty()) {
            return 0;
        } else {
            Ob front = m_queue.front();
            m_queue.pop_front();
            m_set.erase(front);
            return front;
        }
    }
};

static UniqueFifoQueue g_merge_queue;

void schedule_merge (Ob dep)
{
    g_merge_queue.push(dep);
}

void process_mergers (Signature & signature)
{
    POMAGMA_INFO("Processing mergers");
    Carrier & carrier = * signature.carrier();

    size_t merge_count = 0;
    while (Ob dep = g_merge_queue.pop()) {
        POMAGMA_DEBUG("merging " << dep);
        const Ob rep = carrier.find(dep);
        POMAGMA_ASSERT(dep > rep, "ill-formed merge: " << dep << ", " << rep);

#define POMAGMA_MERGE(arity)\
        for (auto i : signature.arity()) { i.second->unsafe_merge(dep); }

        // order by most-likely-to-merge
        POMAGMA_MERGE(binary_functions);
        POMAGMA_MERGE(symmetric_functions);
        POMAGMA_MERGE(injective_functions);
        POMAGMA_MERGE(nullary_functions);
        POMAGMA_MERGE(binary_relations);

#undef POMAGMA_MERGE

        carrier.unsafe_remove(dep);
        ++merge_count;
    }

    POMAGMA_INFO("processed " << merge_count << " mergers");
}

} // namespace pomagma
