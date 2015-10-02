#pragma once

#include <pomagma/atlas/program_fwd.hpp>
#include <pomagma/atlas/shard/util.hpp>
#include <pomagma/util/sequential/dense_set.hpp>
#include <pomagma/util/threading.hpp>
#include <pomagma/util/util.hpp>
#include <vector>

namespace pomagma {
namespace shard {

// Index maps structure parts to topics.
class Index : noncopyable
{
public:

    typedef vm::Program Program;
    typedef vm::Context_<Ob, DenseSet::RawData> Context;

    Index () : m_frozen(false) {}
    void freeze () { m_frozen = true; }

    // these are set once before freezing
    void insert_unary_relation (uint8_t name, topic_t topic);
    void insert_injective_function (uint8_t name, topic_t topic);
    void insert_binary_relation (uint8_t name, topic_t topic);
    void insert_binary_function (uint8_t name, topic_t topic);
    void insert_symmetric_function (uint8_t name, topic_t topic);

    // these may be reset before or after freezing
    void insert_binary_relation (uint8_t name, topic_t topic, Ob min_lhs);
    void insert_binary_function (uint8_t name, topic_t topic, Ob min_lhs);
    void insert_symmetric_function (uint8_t name, topic_t topic, Ob min_lhs);

    // this may only be called after freezing
    topic_t try_find_cell_to_execute (Program program, Context * context) const;

private:

    // these are not mutex guarded
    topic_t find_unary_relation (uint8_t name) const;
    topic_t find_injective_function (uint8_t name) const;

    // these are mutex guarded
    topic_t find_binary_relation_lhs (uint8_t name, Ob lhs) const;
    topic_t find_binary_relation_all (uint8_t name) const;
    topic_t find_binary_function_lhs (uint8_t name, Ob lhs) const;
    topic_t find_binary_function_all (uint8_t name) const;
    topic_t find_symmetric_function_lhs (uint8_t name, Ob lhs) const;
    topic_t find_symmetric_function_all (uint8_t name) const;

    class ShardedRange
    {
    public:

        // a shared topic for broadcasting
        void insert_all (topic_t topic) { m_all = topic; }
        topic_t find_all () const { return m_all; }

        // topics for each range of lhs
        void insert_lhs (topic_t topic, Ob min_lhs);
        topic_t find_lhs (Ob lhs) const;

    private:

        topic_t m_all;
        std::vector<std::pair<Ob, topic_t>> m_min_lhs;
    };

    std::vector<topic_t> m_unary_relations;
    std::vector<topic_t> m_injective_functions;
    std::vector<ShardedRange> m_binary_relations;
    std::vector<ShardedRange> m_binary_functions;
    std::vector<ShardedRange> m_symmetric_functions;
    SharedMutex m_mutex;
    bool m_frozen;
};

} // namespace shard
} // namespace pomagma
