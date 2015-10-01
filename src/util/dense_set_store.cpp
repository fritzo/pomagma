#include <pomagma/util/dense_set_store.hpp>
#include <pomagma/vendor/farmhash/farmhash.h>

namespace pomagma {

inline SetId fingerprint (const Word * words, size_t byte_dim)
{
    return util::Fingerprint64(reinterpret_cast<const char *>(words), byte_dim);
}

DenseSetStore::DenseSetStore (size_t item_dim) :
    m_item_dim(item_dim),
    m_byte_dim((1 + item_dim) / 8)
{
}

DenseSetStore::~DenseSetStore ()
{
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_INFO("Validating DenseSetStore");
        for (const auto & i : m_index) {
            POMAGMA_ASSERT(
                i.first == fingerprint(i.second, m_byte_dim),
                "DenseSet was changed after storing in DenseSetStore");
        }
    }
}

SetId DenseSetStore::store (DenseSet && set)
{
    POMAGMA_ASSERT1(set.item_dim() == m_item_dim, "size mismatch");
    Word * data = set.raw_data();
    SetId id = fingerprint(data, m_byte_dim);
    auto inserted = m_index.insert({id, data});
    if (inserted.second) {
        DenseSet destructor(std::move(set));
    } else {
        POMAGMA_ASSERT1(
            not memcmp(data, inserted.first->second, m_byte_dim),
            "hash conflict")
    }
    return id;
}

} // namespace pomagma
