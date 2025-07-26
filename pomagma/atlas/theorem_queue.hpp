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

//----------------------------------------------------------------------------
// BinaryTheoremQueue - Handles function equality constraints

class BinaryFunctionTheoremQueue : noncopyable {
    struct Task {
        Ob lhs, rhs, val;
    };

    struct Hash {
        size_t operator()(const Task& task) const {
            return FastObHash::hash(task.lhs, task.rhs, task.val);
        }
    };

    struct Eq {
        bool operator()(const Task& task1, const Task& task2) const {
            return task1.lhs == task2.lhs and task1.rhs == task2.rhs and
                   task1.val == task2.val;
        }
    };

    std::unordered_set<Task, Hash, Eq> m_tasks;
    std::mutex m_mutex;

   public:
    BinaryFunctionTheoremQueue() = default;

    template <class Function>
    void infer_equal(const Function& FUN, Ob lhs1, Ob rhs1, Ob lhs2, Ob rhs2) {
        Ob val1 = FUN.find(lhs1, rhs1);
        Ob val2 = FUN.find(lhs2, rhs2);
        if (unlikely(val1 != val2)) {
            if (val2 == 0 or (val1 != 0 and val2 > val1)) {
                m_tasks.insert({lhs2, rhs2, val1});
            } else {
                m_tasks.insert({lhs1, rhs1, val2});
            }
        }
    }

    void delegate_to(BinaryFunctionTheoremQueue& master) {
        std::unique_lock<std::mutex> lock(master.m_mutex);
        master.m_tasks.insert(m_tasks.begin(), m_tasks.end());
        m_tasks.clear();
    }

    template <class Function>
    size_t process(Structure& structure, Function& FUN) {
        for (const Task& task : m_tasks) {
            FUN.insert(task.lhs, task.rhs, task.val);
        }
        size_t theorem_count = m_tasks.size();
        m_tasks.clear();
        process_mergers(structure.signature());
        return theorem_count;
    }

    ~BinaryFunctionTheoremQueue() {
        POMAGMA_ASSERT1(m_tasks.empty(), "unprocessed tasks remain");
    }
};

}  // namespace pomagma