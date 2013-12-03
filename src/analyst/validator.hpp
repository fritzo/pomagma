#pragma once

#include <pomagma/analyst/approximate.hpp>
#include <pomagma/analyst/corpus.hpp>
#include <set>
#include <thread>
#include <mutex>

namespace pomagma
{

class Validator
{
public:

    Validator (
            Approximator & approximator,
            size_t thread_count = 1);
    ~Validator ();

    void update (const Corpus::Diff & diff);
    Approximator::Validity is_valid (const Corpus::Term * term);

private:

    void cancel (const Corpus::Term * term);
    void schedule (const Corpus::Term * term);

    struct Task
    {
        Corpus::Term * work;
        size_t priority;
        std::set<Task *> references;
    };

    Task * get_work ();

    Approximator & m_approximator;
    std::mutex m_mutex;
    std::unordered_map<const Corpus::Term *, Approximation *> m_cache;
    std::vector<std::thread> m_workers;
};

} // namespace pomagma
