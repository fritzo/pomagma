#include "scheduler.hpp"
#include <vector>
#include <atomic>
#include "threading.hpp"
#include <thread>
#include <mutex>
#include <chrono>
#include <tbb/concurrent_queue.h>


namespace pomagma
{

namespace Scheduler
{

static std::atomic<bool> g_alive(false);
static std::atomic<uint_fast64_t> g_merge_count(0);
static std::atomic<uint_fast64_t> g_enforce_count(0);
static std::mutex g_work_mutex;
static std::condition_variable g_work_condition;
static SharedMutex g_strict_mutex;
static std::vector<std::thread> g_threads;

void cancel_tasks_referencing (Ob dep);

template<class Task>
class TaskQueue
{
    tbb::concurrent_queue<Task> m_queue;

public:

    void push (const Task & task)
    {
        m_queue.push(task);
        g_work_condition.notify_one();
    }

    bool try_execute ()
    {
        SharedMutex::SharedLock lock(g_strict_mutex);
        Task task;
        if (m_queue.try_pop(task)) {
            execute(task);
            return true;
        } else {
            return false;
        }
    }

    void cancel_referencing (Ob dep)
    {
        tbb::concurrent_queue<Task> queue;
        std::swap(queue, m_queue);
        for (Task task; queue.try_pop(task);) {
            if (not task.references(dep)) {
                push(task);
            }
        }
    }
};

template<>
class TaskQueue<MergeTask>
{
    tbb::concurrent_queue<MergeTask> m_queue;

public:

    void push (const MergeTask & task)
    {
        m_queue.push(task);
        g_work_condition.notify_one();
    }

    bool try_execute ()
    {
        MergeTask task;
        if (m_queue.try_pop(task)) {
            SharedMutex::UniqueLock lock(g_strict_mutex);
            execute(task);
            cancel_tasks_referencing(task.dep);
            return true;
        } else {
            return false;
        }
    }
};

template<>
class TaskQueue<ResizeTask>
{
    // TODO
};

static TaskQueue<MergeTask> g_mergers;
//static TaskQueue<ResizeTask> g_resize_tasks; // TODO
static TaskQueue<CleanupTask> g_cleanups;
static TaskQueue<ExistsTask> g_exists_tasks;
static TaskQueue<PositiveOrderTask> g_positive_orders;
static TaskQueue<NegativeOrderTask> g_negative_orders;
static TaskQueue<NullaryFunctionTask> g_nullary_functions;
static TaskQueue<InjectiveFunctionTask> g_injective_functions;
static TaskQueue<BinaryFunctionTask> g_binary_functions;
static TaskQueue<SymmetricFunctionTask> g_symmetric_functions;


inline bool try_work ()
{
    return g_mergers.try_execute()
        or g_exists_tasks.try_execute()
        or g_nullary_functions.try_execute()
        or g_injective_functions.try_execute()
        or g_binary_functions.try_execute()
        or g_symmetric_functions.try_execute()
        or g_positive_orders.try_execute()
        or g_negative_orders.try_execute()
        or g_cleanups.try_execute();
}

inline void cancel_tasks_referencing (Ob dep)
{
    g_exists_tasks.cancel_referencing(dep);
    g_nullary_functions.cancel_referencing(dep);
    g_injective_functions.cancel_referencing(dep);
    g_binary_functions.cancel_referencing(dep);
    g_symmetric_functions.cancel_referencing(dep);
    g_positive_orders.cancel_referencing(dep);
    g_negative_orders.cancel_referencing(dep);
}

void do_work ()
{
    const auto timeout = std::chrono::seconds(60);
    while (g_alive) {
        if (not try_work()) {
            std::unique_lock<std::mutex> lock(g_work_mutex);
            g_work_condition.wait_for(lock, timeout);
        }
    }
}

void start (size_t thread_count)
{
    g_alive = true;
    for (size_t i = 0; i < thread_count; ++i) {
        g_threads.push_back(std::thread(do_work));
    }
}

void stopall ()
{
    g_alive = false;
    g_work_condition.notify_all();
    while (not g_threads.empty()) {
        g_threads.back().join();
        g_threads.pop_back();
    }
}

} // namespace Scheduler


void schedule (const MergeTask & task)
{
    Scheduler::g_mergers.push(task);
}

void schedule (const ResizeTask &)
{
    TODO("Scheduler::g_resize_tasks.push(task);");
}

void schedule (const CleanupTask & task)
{
    Scheduler::g_cleanups.push(task);
}

void schedule (const ExistsTask & task)
{
    Scheduler::g_exists_tasks.push(task);
}

void schedule (const PositiveOrderTask & task)
{
    Scheduler::g_positive_orders.push(task);
}

void schedule (const NegativeOrderTask & task)
{
    Scheduler::g_negative_orders.push(task);
}

void schedule (const NullaryFunctionTask & task)
{
    Scheduler::g_nullary_functions.push(task);
}

void schedule (const InjectiveFunctionTask & task)
{
    Scheduler::g_injective_functions.push(task);
}

void schedule (const BinaryFunctionTask & task)
{
    Scheduler::g_binary_functions.push(task);
}

void schedule (const SymmetricFunctionTask & task)
{
    Scheduler::g_symmetric_functions.push(task);
}

} // namespace pomagma
