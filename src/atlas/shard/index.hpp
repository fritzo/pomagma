#pragma once

#include <pomagma/atlas/program_fwd.hpp>
#include <pomagma/atlas/shard/util.hpp>
#include <pomagma/util/sequential/dense_set.hpp>
#include <pomagma/util/threading.hpp>
#include <pomagma/util/util.hpp>
#include <vector>

namespace pomagma {
namespace shard {

class Index
{
public:

    typedef vm::Program Program;
    typedef vm::Context_<Ob, DenseSet::RawData> Context;

    // these are set once at initialization
    void register_unary_relation (uint8_t name, topic_t topic);
    void register_unary_function (uint8_t name, topic_t topic);

    // these may be reset during inference as cells split
    void register_binary_relation (uint8_t name, topic_t topic, Ob min_lhs);
    void register_binary_function (uint8_t name, topic_t topic, Ob min_lhs);
    void register_symmetric_function (uint8_t name, topic_t topic, Ob min_lhs);

    topic_t try_find_cell_to_execute (Program program, Context * context) const;

private:

    // these are not mutex guarded
    topic_t find_unary_relation (uint8_t name) const;
    topic_t find_injective_function (uint8_t name) const;

    // these are mutex guarded
    topic_t find_binary_relation_lhs (uint8_t name, Ob ob) const;
    topic_t find_binary_relation_all (uint8_t name) const;
    topic_t find_binary_function_lhs (uint8_t name, Ob ob) const;
    topic_t find_binary_function_all (uint8_t name) const;
    topic_t find_symmetric_function_lhs (uint8_t name, Ob ob) const;
    topic_t find_symmetric_function_all (uint8_t name) const;

    std::vector<topic_t> m_unary_relations;
    std::vector<topic_t> m_unary_functions;
    std::vector<std::vector<Ob, topic_t>> m_binary_relations;
    std::vector<std::vector<Ob, topic_t>> m_binary_functions;
    std::vector<std::vector<Ob, topic_t>> m_ymmetric_functions;
    mutable SharedMutex m_mutex;
};

} // namespace shard
} // namespace pomagma
