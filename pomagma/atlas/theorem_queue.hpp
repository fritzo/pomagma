#pragma once

#include <mutex>
#include <pomagma/util/sort_uniq.hpp>
#include <unordered_set>
#include <utility>
#include <vector>

namespace pomagma {

class BinaryRelationTheoremQueue {
    BinaryRelation& m_rel;
    std::vector<std::pair<Ob, Ob>> m_queue;

   public:
    explicit BinaryRelationTheoremQueue(BinaryRelation& rel) : m_rel(rel) {}
    ~BinaryRelationTheoremQueue() {
        POMAGMA_ASSERT(m_queue.empty(), "theorems have not been flushed");
    }

    void push(Ob x, Ob y) { m_queue.push_back(std::make_pair(x, y)); }

    void try_push(Ob x, Ob y) {
        if (unlikely(not m_rel.find(x, y))) {
            push(x, y);
        }
    }

    void flush(std::mutex& mutex) {
        if (m_queue.empty()) return;
        sort_uniq(m_queue);
        {
            std::unique_lock<std::mutex> lock(mutex);
            for (const auto& pair : m_queue) {
                m_rel.insert(pair.first, pair.second);
            }
        }
        m_queue.clear();
    }
};

class BinaryRelationRowTheoremQueue {
    BinaryRelation& m_rel;
    Ob m_lhs;
    DenseSet m_rhs;

   public:
    explicit BinaryRelationRowTheoremQueue(BinaryRelation& rel)
        : m_rel(rel), m_lhs(0), m_rhs(rel.item_dim()) {}

    void push(Ob lhs, Ob rhs) {
        POMAGMA_ASSERT1(
            m_lhs == 0 or m_lhs == lhs,
            "mismatched lhs in LhsFixedTheoremQueue; use TheoremQueue instead");
        m_lhs = lhs;
        m_rhs.insert(rhs);
    }

    void flush(std::mutex& mutex) {
        if (m_lhs == 0) return;
        {
            std::unique_lock<std::mutex> lock(mutex);
            m_rel.insert(m_lhs, m_rhs);
        }
        m_lhs = 0;
        m_rhs.zero();
    }
};

}  // namespace pomagma