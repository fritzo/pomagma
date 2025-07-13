#pragma once

#include <map>
#include <pomagma/util/threading.hpp>
#include <pomagma/util/util.hpp>
#include <unordered_map>
#include <unordered_set>

#define POMAGMA_LINE_PROFILER (false)

namespace pomagma {

// Instances are typically thread local

class ProgramProfiler : noncopyable {
    struct Stat {
        size_t count;
        size_t time;

        void report_to(Stat &manager) noexcept {
            manager.count += count;
            manager.time += time;
            count = 0;
            time = 0;
        }
    };

   public:
    ProgramProfiler() noexcept;
    ~ProgramProfiler() noexcept;

    class Block : noncopyable {
        ProgramProfiler &m_profiler;
        Stat &m_stat;
        Timer m_timer;

       public:
        Block(ProgramProfiler &profiler, const uint8_t *program,
              const std::vector<uint8_t> &programs,
              std::vector<uint32_t> &histogram)
            : m_profiler(profiler), m_stat(profiler.m_stats[program]) {
            m_profiler.sample_start(programs, histogram);
        }

        ~Block() noexcept {
            m_profiler.sample_stop();
            m_stat.count += 1;
            m_stat.time += m_timer.elapsed_us();
        }
    };

#if POMAGMA_LINE_PROFILER
    void sample_start(const std::vector<uint8_t> &programs,
                      std::vector<uint32_t> &histogram) noexcept {
        m_programs = programs.data();
        m_histogram = histogram.data();
        m_last_sample_line = nullptr;
        m_last_sample_time = FastClock::now();
    }

    void sample(const uint8_t *program) noexcept {
        uint64_t current_time = FastClock::now();

        // Attribute elapsed time to the last sample
        if (m_last_sample_line != nullptr) {
            uint64_t elapsed_ns = current_time - m_last_sample_time;
            uint64_t random_dither = FastRNG::next() % target_interval_ns;
            uint64_t total = elapsed_ns + random_dither;
            uint64_t samples = total / target_interval_ns;
            if (unlikely(samples)) {
                size_t offset = m_last_sample_line - m_programs;
                std::atomic<uint32_t> *count =
                    reinterpret_cast<std::atomic<uint32_t> *>(m_histogram +
                                                              offset);
                count->fetch_add(samples, std::memory_order_relaxed);
            }
        }

        // Prepare for next sample
        m_last_sample_time = current_time;
        m_last_sample_line = program;
    }

    void sample_stop() noexcept { sample(nullptr); }
#else   // POMAGMA_LINE_PROFILER
    void sample_start(const std::vector<uint8_t> &,
                      std::vector<uint32_t> &) noexcept {}
    void sample_stop() noexcept {}
    void sample(const uint8_t *) noexcept {}
#endif  // POMAGMA_LINE_PROFILER

    static void log_stats(const std::map<const void *, size_t> &linenos);

   private:
    inline void unsafe_report() noexcept;
    struct LogLine;

#if POMAGMA_LINE_PROFILER
    static constexpr uint64_t target_interval_ns = 10'000'000;  // 10ms
    uint64_t m_last_sample_time;
    const uint8_t *m_last_sample_line;
    const uint8_t *m_programs = nullptr;
    uint32_t *m_histogram = nullptr;
#endif  // POMAGMA_LINE_PROFILER
    std::unordered_map<const void *, Stat> m_stats;

    static std::mutex s_mutex;
    static std::unordered_set<ProgramProfiler *> s_instances;
    static std::unordered_map<const void *, Stat> s_stats;
};

}  // namespace pomagma
