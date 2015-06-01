#pragma once

#include <pomagma/util/threading.hpp>
#include <thread>
#include <future>
#include <tbb/concurrent_queue.h>

namespace pomagma
{

template<class Task, class Processor>
class WorkerPool : noncopyable
{
    Processor & m_processor;
    std::atomic<bool> m_accepting;
    tbb::concurrent_queue<Task> m_queue;
    std::mutex m_mutex;
    std::condition_variable m_condition;
    std::vector<std::thread> m_pool;

public:

    WorkerPool (Processor & processor, size_t thread_count)
        : m_processor(processor),
          m_accepting(true)
    {
        POMAGMA_ASSERT_LT(0, thread_count);
        POMAGMA_DEBUG("Starting pool of " << thread_count << " workers");
        for (size_t i = 0; i < thread_count; ++i) {
            m_pool.push_back(std::thread([this](){ this->do_work(); }));
        }
    }

    void schedule (const Task & task)
    {
        POMAGMA_ASSERT(m_accepting.load(), "pool is not accepting work");
        m_queue.push(task);
        m_condition.notify_one();
    }

    void wait ()
    {
        bool expected = true;
        if (m_accepting.compare_exchange_strong(expected, false)) {
            m_condition.notify_all();
            for (auto & worker : m_pool) {
                worker.join();
            }
            POMAGMA_DEBUG("Stopped pool of " << m_pool.size() << " workers");
        }
    }

    ~WorkerPool () { wait(); }

private:

    void do_work ()
    {
        Task task;
        while (likely(m_accepting.load())) {
            if (m_queue.try_pop(task)) {
                m_processor(task);
            } else {
                std::unique_lock<std::mutex> lock(m_mutex);
                m_condition.wait_for(lock, std::chrono::seconds(60));
            }
        }
        while (m_queue.try_pop(task)) {
            m_processor(task);
        }
    }
};

} // namespace pomagma
