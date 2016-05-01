#include <pomagma/util/dense_set_store.hpp>
#include <pomagma/third_party/farmhash/farmhash.h>

namespace pomagma {

inline SetId fingerprint(const Word *words, size_t byte_dim) {
    return util::Fingerprint64(reinterpret_cast<const char *>(words), byte_dim);
}

DenseSetStore::DenseSetStore(size_t item_dim)
    : m_item_dim(item_dim), m_byte_dim(1 + item_dim / 8) {}

DenseSetStore::~DenseSetStore() {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_INFO("Validating DenseSetStore");
        for (const auto &i : m_index) {
            POMAGMA_ASSERT(
                i.first == fingerprint(i.second, m_byte_dim),
                "DenseSet was changed after storing in DenseSetStore");
        }
    }
}

inline Word *DenseSetStore::insert(SetId id, Word *data) {
    SharedMutex::UniqueLock lock(m_mutex);
    return m_index.insert({id, data}).first->second;
}

SetId DenseSetStore::store(DenseSet &&set) {
    POMAGMA_ASSERT1(set.item_dim() == m_item_dim, "size mismatch");
    Word *data = set.raw_data();
    SetId id = fingerprint(data, m_byte_dim);
    Word *stored = insert(id, data);
    if (data == stored) {
        set.move_ownership();
    } else {
        POMAGMA_ASSERT(not memcmp(data, stored, m_byte_dim), "hash conflict")
    }
    return id;
}

}  // namespace pomagma
