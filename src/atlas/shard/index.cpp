#include "index.hpp"
#include <algorithm>
#include <pomagma/atlas/program.hpp>

namespace pomagma {
namespace shard {

inline void Index::ShardedRange::register_lhs (topic_t topic, Ob min_lhs)
{
    std::pair<Ob, topic_t> pair(min_lhs, 0);
    auto i = std::lower_bound(m_min_lhs.begin(), m_min_lhs.end(), pair);
    m_min_lhs.insert(i, std::make_pair(min_lhs, topic));
}

inline topic_t Index::ShardedRange::find_lhs (Ob lhs) const
{
    std::pair<Ob, topic_t> pair(lhs, 0);
    auto i = std::lower_bound(m_min_lhs.begin(), m_min_lhs.end(), pair);
    POMAGMA_ASSERT1(i != m_min_lhs.end(), "missing lhs: " << lhs);
    return i->second;
}

inline topic_t Index::find_unary_relation (uint8_t name) const
{
    POMAGMA_ASSERT1(name < m_unary_relations.size(),
        "unknown unary_relation: " << name);
    return m_unary_relations[name];
}

inline topic_t Index::find_binary_relation_lhs (uint8_t name, Ob lhs) const
{
    POMAGMA_ASSERT1(name < m_binary_relations.size(),
        "unknown binary_relation: " << name);
    SharedMutex::SharedLock lock(m_mutex);
    return m_binary_relations[name].find_lhs(lhs);
}

inline topic_t Index::find_binary_relation_all (uint8_t name) const
{
    POMAGMA_ASSERT1(name < m_binary_relations.size(),
        "unknown binary_relation: " << name);
    return m_binary_relations[name].find_all();
}

inline topic_t Index::find_injective_function (uint8_t name) const
{
    POMAGMA_ASSERT1(name < m_injective_functions.size(),
        "unknown injective_function: " << name);
    return m_injective_functions[name];
}

inline topic_t Index::find_binary_function_lhs (uint8_t name, Ob lhs) const
{
    POMAGMA_ASSERT1(name < m_binary_functions.size(),
        "unknown binary_relation: " << name);
    SharedMutex::SharedLock lock(m_mutex);
    return m_binary_functions[name].find_lhs(lhs);
}

inline topic_t Index::find_binary_function_all (uint8_t name) const
{
    POMAGMA_ASSERT1(name < m_binary_functions.size(),
        "unknown binary_function: " << name);
    return m_binary_functions[name].find_all();
}

inline topic_t Index::find_symmetric_function_lhs (uint8_t name, Ob lhs) const
{
    POMAGMA_ASSERT1(name < m_symmetric_functions.size(),
        "unknown symmetric_relation: " << name);
    SharedMutex::SharedLock lock(m_mutex);
    return m_symmetric_functions[name].find_lhs(lhs);
}

inline topic_t Index::find_symmetric_function_all (uint8_t name) const
{
    POMAGMA_ASSERT1(name < m_symmetric_functions.size(),
        "unknown symmetric_function: " << name);
    return m_symmetric_functions[name].find_all();
}

topic_t Index::try_find_cell_to_execute (
        Program program,
        Context * context) const
{
    using namespace vm;

    const OpCode op_code = static_cast<OpCode>(program[0]);
    const uint8_t & name = program[1];
    const uint8_t * args = program + 2;

    switch (op_code) {

        // These can execute in any cell.
        case PADDING:
        case SEQUENCE:
        case GIVEN_EXISTS:
        case GIVEN_UNARY_RELATION:
        case GIVEN_BINARY_RELATION:
        case GIVEN_NULLARY_FUNCTION:
        case GIVEN_INJECTIVE_FUNCTION:
        case GIVEN_BINARY_FUNCTION:
        case GIVEN_SYMMETRIC_FUNCTION:
        case FOR_NEG:
        case FOR_NEG_NEG:
        case FOR_POS_NEG:
        case FOR_POS_NEG_NEG:
        case FOR_POS_POS:
        case FOR_POS_POS_NEG:
        case FOR_POS_POS_NEG_NEG:
        case FOR_POS_POS_POS:
        case FOR_POS_POS_POS_POS:
        case FOR_POS_POS_POS_POS_POS:
        case FOR_POS_POS_POS_POS_POS_POS:
        case FOR_ALL:
        case FOR_NULLARY_FUNCTION:
        case FOR_BLOCK:
        case IF_BLOCK:
        case IF_EQUAL:
        case IF_NULLARY_FUNCTION:
        case LET_NULLARY_FUNCTION:
        case INFER_NULLARY_NULLARY:
        case INFER_EQUAL:
        case INFER_NULLARY_FUNCTION:
            return 0;

        case LETS_UNARY_RELATION:
        case FOR_UNARY_RELATION:
        case IF_UNARY_RELATION:
        case INFER_UNARY_RELATION:
            return find_unary_relation(name);

        case LETS_BINARY_RELATION_LHS:
        case FOR_BINARY_RELATION_LHS:
        case IF_BINARY_RELATION:
        case INFER_BINARY_RELATION:
            return find_binary_relation_lhs(name, context->obs[args[0]]);

        case LETS_BINARY_RELATION_RHS:
        case FOR_BINARY_RELATION_RHS:
            return find_binary_relation_all(name);

        case LETS_INJECTIVE_FUNCTION:
        case LETS_INJECTIVE_FUNCTION_INVERSE:
        case FOR_INJECTIVE_FUNCTION:
        case FOR_INJECTIVE_FUNCTION_KEY:
        case FOR_INJECTIVE_FUNCTION_VAL:
        case IF_INJECTIVE_FUNCTION:
        case LET_INJECTIVE_FUNCTION:
        case INFER_INJECTIVE_FUNCTION:
        case INFER_NULLARY_INJECTIVE:
            return find_injective_function(name);

        case LETS_BINARY_FUNCTION_LHS:
        case FOR_BINARY_FUNCTION_LHS:
        case FOR_BINARY_FUNCTION_LHS_VAL:
        case FOR_BINARY_FUNCTION_LHS_RHS:
        case IF_BINARY_FUNCTION:
        case LET_BINARY_FUNCTION:
        case INFER_BINARY_FUNCTION:
        case INFER_NULLARY_BINARY:
            return find_binary_function_lhs(name, context->obs[args[0]]);

        case LETS_BINARY_FUNCTION_RHS:
        case FOR_BINARY_FUNCTION_RHS:
        case FOR_BINARY_FUNCTION_VAL:
        case FOR_BINARY_FUNCTION_RHS_VAL:
            return find_binary_function_all(name);

        case LETS_SYMMETRIC_FUNCTION_LHS:
        case FOR_SYMMETRIC_FUNCTION_LHS:
        case FOR_SYMMETRIC_FUNCTION_LHS_VAL:
        case FOR_SYMMETRIC_FUNCTION_LHS_RHS:
        case IF_SYMMETRIC_FUNCTION:
        case LET_SYMMETRIC_FUNCTION:
        case INFER_SYMMETRIC_FUNCTION:
        case INFER_NULLARY_SYMMETRIC:
            return find_symmetric_function_lhs(name, context->obs[args[0]]);

        case FOR_SYMMETRIC_FUNCTION_VAL:
            return find_symmetric_function_all(name);

        case INFER_INJECTIVE_INJECTIVE:
        case INFER_BINARY_BINARY:
        case INFER_SYMMETRIC_SYMMETRIC:
        case INFER_INJECTIVE_BINARY:
        case INFER_INJECTIVE_SYMMETRIC:
        case INFER_BINARY_SYMMETRIC:
            POMAGMA_ERROR("cannot join across cells");
    }

    POMAGMA_ERROR("unreachable");
}

} // namespace shard
} // namespace pomagma
