#pragma once

#include <pomagma/microstructure/util.hpp>
#include <pomagma/platform/threading.hpp>
#include <atomic>
#include <thread>
#include <vector>

namespace pomagma
{

class CleanupProfiler
{
    static std::vector<atomic_default<unsigned long>> s_counts;
    static std::vector<atomic_default<unsigned long>> s_elapsed;

public:

    class Block
    {
        const unsigned long m_type;
        Timer m_timer;
    public:
        Block (unsigned long type) : m_type(type) {}
        ~Block ()
        {
            s_elapsed[m_type].fetch_add(
                m_timer.elapsed_us(),
                std::memory_order_acq_rel);
            s_counts[m_type].fetch_add(1, std::memory_order_acq_rel);
        }
    };

    static void init (unsigned long task_count)
    {
        s_counts.resize(task_count);
        s_elapsed.resize(task_count);
    }

    static void cleanup ()
    {
        unsigned long task_count = s_counts.size();
        POMAGMA_INFO("Task Id\tCount\tElapsed sec");
        for (unsigned long i = 0; i < task_count; ++i) {
            POMAGMA_INFO(
                std::setw(4) << i <<
                std::setw(8) << s_counts[i].load() <<
                std::setw(16) << (s_elapsed[i].load() * 1e-6));
        }
    }

    // DEPRECATED
    CleanupProfiler (unsigned long task_count) { init(task_count); }
};

} // namespace pomagma
