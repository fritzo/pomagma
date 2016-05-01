#include "profiler.hpp"
#include <algorithm>

namespace pomagma {

std::mutex ProgramProfiler::s_mutex;
std::unordered_set<ProgramProfiler *> ProgramProfiler::s_instances;
std::unordered_map<const void *, ProgramProfiler::Stat>
    ProgramProfiler::s_stats;

inline void ProgramProfiler::unsafe_report() {
    for (auto &pair : m_stats) {
        pair.second.report_to(s_stats[pair.first]);
    }
}

ProgramProfiler::ProgramProfiler() {
    std::unique_lock<std::mutex> lock(s_mutex);
    s_instances.insert(this);
}

ProgramProfiler::~ProgramProfiler() {
    std::unique_lock<std::mutex> lock(s_mutex);
    unsafe_report();
    s_instances.erase(this);
}

struct ProgramProfiler::LogLine {
    Stat stat;
    size_t lineno;

    bool operator<(const LogLine &other) const {
        return stat.time > other.stat.time;
    }
};

void ProgramProfiler::log_stats(const std::map<const void *, size_t> &linenos) {
    std::unique_lock<std::mutex> lock(s_mutex);
    for (ProgramProfiler *instance : s_instances) {
        instance->unsafe_report();
    }

    std::vector<LogLine> log_lines;
    double total_sec = 0;
    for (auto &pair : s_stats) {
        size_t lineno = map_find(linenos, pair.first);
        Stat &stat = pair.second;
        log_lines.push_back({stat, lineno});
        total_sec += stat.time * 1e-6;
        stat.count = 0;
        stat.time = 0;
    }
    std::sort(log_lines.begin(), log_lines.end());

    POMAGMA_INFO("Profile of VirtualMachine programs:");
    POMAGMA_INFO(" Line       Calls Percent   Total sec Per call sec");
    POMAGMA_INFO("----- ----------- ------- ----------- ------------");
    for (const auto &line : log_lines) {
        double time_sec = line.stat.time * 1e-6;
        double percent = 100 * time_sec / total_sec;
        POMAGMA_INFO(std::fixed << std::setprecision(2) << std::setw(5)
                                << std::right << line.lineno << std::setw(12)
                                << std::right << line.stat.count << std::setw(8)
                                << std::right << percent << std::setw(12)
                                << time_sec << std::setw(10)
                                << (time_sec / line.stat.count));
    }
}

}  // namespace pomagma
