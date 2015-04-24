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

    const unsigned long m_type;
    Timer m_timer;

public:

    CleanupProfiler (unsigned long type) : m_type(type) {}
    ~CleanupProfiler ()
    {
        s_elapsed[m_type].fetch_add(
            m_timer.elapsed_us(),
            std::memory_order_acq_rel);
        s_counts[m_type].fetch_add(1, std::memory_order_acq_rel);
    }

    static void init (unsigned long task_count)
    {
        s_counts.resize(task_count);
        s_elapsed.resize(task_count);
    }

    static void log_stats ()
    {
        unsigned long task_count = s_counts.size();

        double total_sec = 0;
        for (unsigned long i = 0; i < task_count; ++i) {
            double time_sec = s_elapsed[i].load() * 1e-6;
            total_sec += time_sec;
        }

        POMAGMA_INFO("Id    Calls Percent Total sec   Per call sec");
        POMAGMA_INFO("--------------------------------------------");
        for (unsigned long i = 0; i < task_count; ++i) {
            size_t count = s_counts[i].load();
            double time_sec = s_elapsed[i].load() * 1e-6;
            std::ostringstream percent;
            percent <<
                std::setw(6) <<
                std::right << std::fixed << std::setprecision(2) <<
                (100 * time_sec / total_sec) << "  ";
            POMAGMA_INFO(
                std::setw(6) << i <<
                std::setw(6) << count <<
                percent.str() <<
                std::setw(12) << time_sec <<
                std::setw(12) << (time_sec / count));
        }
    }
};

} // namespace pomagma
