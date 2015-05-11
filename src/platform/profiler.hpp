#pragma once

#include <pomagma/platform/threading.hpp>
#include <atomic>
#include <thread>
#include <vector>
#include <map>
#include <unordered_map>
#include <unordered_set>

namespace pomagma
{

class ProgramProfiler : noncopyable
{
    struct Stat
    {
        size_t count;
        size_t time;

        void report_to (Stat & manager)
        {
            manager.count += count;
            manager.time += time;
            count = 0;
            time = 0;
        }
    };

public:

    ProgramProfiler ();
    ~ProgramProfiler ();

    static void log_stats (const std::map<const void *, size_t> & linenos);

    class Block : noncopyable
    {
        Stat & m_stat;
        Timer m_timer;

    public:

        Block (ProgramProfiler & profiler, const void * program)
            : m_stat(profiler.m_stats[program])
        {
        }

        ~Block ()
        {
            m_stat.count += 1;
            m_stat.time += m_timer.elapsed_us();
        }
    };

private:

    void unsafe_report ();
    struct LogLine;

    std::unordered_map<const void *, Stat> m_stats;

    static std::mutex s_mutex;
    static std::unordered_set<ProgramProfiler *> s_instances;
    static std::unordered_map<const void *, Stat> s_stats;
};

} // namespace pomagma
