#pragma once

#include <pomagma/platform/threading.hpp>
#include <thread>
#include <future>
#include <tbb/concurrent_queue.h>

namespace pomagma
{

template<class Task>
class WorkerPool : noncopyable
{
    std::atomic<bool> m_alive;
    tbb::concurrent_queue<Task> m_work_queue;
    static std::mutex m_work_mutex;
    static std::condition_variable m_work_condition;
    std::vector<std::thread> m_pool;

public:

    WorkerPool (size_t thread_count)
        : m_alive(true)
    {
        for (size_t i = 0; i < thread_count; ++i) {
            m_pool.push_back(std::thread([this](){ this->do_work(); }));
        }
    }
    ~WorkerPool ()
    {
        m_alive = false;
        m_work_condition.notify_all();
        for (auto & worker : m_pool) {
            worker.join();
        }
    }

    void schedule (const Task & task)
    {
        m_work_queue.push(task);
        m_work_condition.notify_one();
    }

private:

    void do_work ()
    {
        while (likely(m_alive)) {
            Task task;
            if (m_work_queue.try_pop(task)) {
                task();
            } else {
                std::unique_lock<std::mutex> lock(m_work_mutex);
                const auto timeout = std::chrono::seconds(60);
                m_work_condition.wait_for(lock, timeout);
                //m_work_condition.wait(lock);
            }
        }
    }
};

} // namespace pomagma
