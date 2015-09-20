#pragma once

#include <condition_variable>
#include <mutex>
#include <pomagma/util/threading.hpp>
#include <queue>
#include <thread>
#include <vector>

namespace pomagma
{

class WorkerPool : noncopyable
{
    std::mutex m_mutex;
    std::condition_variable m_condition;
    std::queue<std::function<void()>> m_queue;
    std::vector<std::thread> m_threads;
    bool m_accepting;

public:

    WorkerPool (size_t thread_count) : m_accepting(true)
    {
        POMAGMA_ASSERT_LT(0, thread_count);
        POMAGMA_DEBUG("Starting pool of " << thread_count << " workers");
        for (size_t i = 0; i < thread_count; ++i) {
            m_threads.emplace_back([this]{
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(m_mutex);
                        m_condition.wait(lock, [this]{
                            return not m_accepting or not m_queue.empty();
                        });
                        if (unlikely(not m_accepting)) {
                            return;
                        }
                        task = std::move(m_queue.front());
                        m_queue.pop();
                    }
                    task();
                }
            });
        }
    }

    ~WorkerPool ()
    {
        {
            std::unique_lock<std::mutex> lock(m_mutex);
            m_accepting = false;
        }
        m_condition.notify_all();
        for (auto & thread : m_threads) {
            thread.join();
        }
    }

    void schedule (std::function<void()> && task)
    {
        {
            std::unique_lock<std::mutex> lock(m_mutex);
            POMAGMA_ASSERT(m_accepting, "pool is not accepting tasks");
            m_queue.emplace(task);
        }
        m_condition.notify_one();
    }
};

} // namespace pomagma
