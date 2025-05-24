#pragma once

#include <pomagma/atlas/macro/structure_impl.hpp>
#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/util/dense_set_store.hpp>
#include <pomagma/util/lazy_map.hpp>
#include <pomagma/util/trool.hpp>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

// declared in pomagma/third_party/farmhash/farmhash.h
namespace util {
uint64_t Fingerprint64(const char *s, size_t len);
}

namespace pomagma {
namespace intervals {

enum Parity { ABOVE, BELOW, NABOVE, NBELOW };
enum Target { LHS, RHS, VAL };

struct Approximation {
    SetId bounds[4];  // one for each Parity

    SetId &operator[](Parity p) { return bounds[p]; }
    SetId operator[](Parity p) const { return bounds[p]; }

    bool operator==(const Approximation &other) const {
        return not memcmp(this, &other, sizeof(Approximation));
    }
    bool operator!=(const Approximation &other) const {
        return memcmp(this, &other, sizeof(Approximation));
    }
};

template <class T>
struct PodHash {
    uint64_t operator()(const T &x) const {
        return util::Fingerprint64(reinterpret_cast<const char *>(&x),
                                   sizeof(T));
    }
};

template <class T>
struct VectorPodHash {
    uint64_t operator()(const std::vector<T> &x) const {
        return util::Fingerprint64(reinterpret_cast<const char *>(x.data()),
                                   x.size() * sizeof(T));
    }
};

template <class T>
struct VectorPodEqual {
    bool operator()(const std::vector<T> &x, const std::vector<T> &y) const {
        return x.size() == y.size() and
               not memcmp(x.data(), y.data(), x.size() * sizeof(T));
    }
};

class Approximator : noncopyable {
   public:
    Approximator(Structure &structure, DenseSetStore &sets,
                 WorkerPool &worker_pool);

    // This expensive operation is for testing.
    bool expensive_refines(const Approximation &lhs,
                           const Approximation &rhs) const;

    // These cheap O(1) operations return immediately with complete results.
    bool observably_differ(const Approximation &lhs,
                           const Approximation &rhs) const;
    Approximation known(Ob ob) const { return m_known[ob]; }
    Approximation unknown() const { return m_unknown; }
    Approximation nullary_function(const std::string &name);
    Approximation less_lhs(const Approximation &lhs);
    Approximation less_rhs(const Approximation &rhs);
    Approximation nless_lhs(const Approximation &lhs);
    Approximation nless_rhs(const Approximation &rhs);

    // These expensive operations immediately return partial cached results and
    // kick off any needed expensive computation for future calls.
    Trool lazy_is_valid(const Approximation &approx);
    Approximation lazy_fuse(const std::vector<Approximation> &messages);
    Approximation lazy_binary_function_lhs_rhs(const std::string &name,
                                               const Approximation &lhs,
                                               const Approximation &rhs);
    Approximation lazy_binary_function_lhs_val(const std::string &name,
                                               const Approximation &lhs,
                                               const Approximation &val);
    Approximation lazy_binary_function_rhs_val(const std::string &,
                                               const Approximation &rhs,
                                               const Approximation &val);

   private:
    Signature &signature() { return m_structure.signature(); }
    static uint64_t hash_name(const std::string &name);

    Trool lazy_disjoint(SetId lhs, SetId rhs);
    SetId lazy_fuse(const std::vector<Approximation> &messages, Parity parity);
    SetId lazy_find(const std::string &name, Target target, Parity parity,
                    SetId arg0, SetId arg1);

    template <class Function>
    SetId function_lhs_rhs(const Function &fun, SetId lhs, SetId rhs,
                           Parity) const;
    template <class Function>
    SetId function_lhs_val(const Function &fun, SetId lhs, SetId val,
                           Parity parity) const;
    template <class Function>
    SetId function_rhs_val(const Function &fun, SetId rhs, SetId val,
                           Parity parity) const;

    void convex_insert(DenseSet &set, Ob ob, bool upward) const;

    // Structure parts.
    Structure &m_structure;
    const size_t m_item_dim;
    const Ob m_top;
    const Ob m_bot;
    const BinaryRelation &m_less;
    const BinaryRelation &m_nless;

    // DenseSet fingerprinting.
    DenseSetStore &m_sets;
    const SetId m_empty_set;
    std::vector<Approximation> m_known;
    Approximation m_unknown;

    // LazyMap caches.
    typedef std::tuple<uint64_t, Target, Parity> CacheKey;
    typedef LazyMap<std::pair<SetId, SetId>, Trool, Trool::MAYBE,
                    PodHash<std::pair<SetId, SetId>>>
        SetPairToTroolCache;
    typedef LazyMap<std::vector<SetId>, SetId, 0, VectorPodHash<SetId>,
                    VectorPodEqual<SetId>>
        SetVectorToSetCache;
    typedef LazyMap<std::pair<SetId, SetId>, SetId, 0,
                    PodHash<std::pair<SetId, SetId>>>
        SetPairToSetCache;

    SetPairToTroolCache m_disjoint_cache;
    SetVectorToSetCache m_union_cache;
    std::unordered_map<std::string, Approximation> m_nullary_cache;
    std::unordered_map<CacheKey, SetPairToSetCache *, PodHash<CacheKey>>
        m_binary_cache;
};

inline bool Approximator::observably_differ(const Approximation &lhs,
                                            const Approximation &rhs) const {
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        if (lhs[p] and rhs[p] and lhs[p] != rhs[p]) return true;
    }
    return false;
}

inline Approximation Approximator::nullary_function(const std::string &name) {
    auto i = m_nullary_cache.find(name);
    POMAGMA_ASSERT(i != m_nullary_cache.end(),
                   "unknown nullary function: " << name);
    return i->second;
}

inline Approximation Approximator::less_lhs(const Approximation &lhs) {
    Approximation rhs = unknown();
    rhs[BELOW] = lhs[BELOW];
    rhs[NABOVE] = lhs[NABOVE];
    return rhs;
}

inline Approximation Approximator::less_rhs(const Approximation &rhs) {
    Approximation lhs = unknown();
    lhs[ABOVE] = rhs[ABOVE];
    lhs[NBELOW] = rhs[NBELOW];
    return lhs;
}

inline Approximation Approximator::nless_lhs(const Approximation &lhs) {
    Approximation rhs = unknown();
    rhs[NBELOW] = lhs[ABOVE];
    return rhs;
}

inline Approximation Approximator::nless_rhs(const Approximation &rhs) {
    Approximation lhs = unknown();
    lhs[NABOVE] = rhs[BELOW];
    return lhs;
}

}  // namespace intervals
}  // namespace pomagma
