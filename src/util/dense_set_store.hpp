#pragma once

#include <pomagma/util/sequential/dense_set.hpp>
#include <pomagma/util/threading.hpp>
#include <unordered_map>

namespace pomagma {

typedef uint64_t SetId;

class DenseSetStore : noncopyable
{
public:

    typedef sequential::DenseSet DenseSet;

    DenseSetStore (size_t item_dim);
    ~DenseSetStore ();

    SetId store (DenseSet && set); // memory is never freed
    DenseSet load (SetId id) const
    {
        SharedMutex::SharedLock lock(m_mutex);
        auto i = m_index.find(id);
        POMAGMA_ASSERT1(i != m_index.end(), "missing id " << id);
        return DenseSet(m_item_dim, i->second);
    }

private:

    struct HashId { SetId operator() (const SetId & id) const { return id; } };

    SharedMutex m_mutex;
    std::unordered_map<SetId, Word *, HashId> m_index;
    const size_t m_item_dim;
    const size_t m_byte_dim;
};

} // namespace pomagma
