#include "scheduler.hpp"
#include <vector>
#include <atomic>
#include "threading.hpp"
#include <boost/thread/thread.hpp>
#include <boost/thread/mutex.hpp>
#include <boost/thread/shared_mutex.hpp>
#include <boost/thread/locks.hpp>
#include <boost/thread/condition_variable.hpp>
#include <boost/date_time/posix_time/posix_time_types.hpp>
#include <tbb/concurrent_queue.h>


namespace pomagma
{

namespace Scheduler
{

static std::atomic<bool> g_alive(false);
static std::atomic<uint_fast64_t> g_merge_count(0);
static std::atomic<uint_fast64_t> g_enforce_count(0);
static boost::mutex g_work_mutex;
static boost::condition_variable g_work_condition;
static SharedMutex g_merge_mutex;
static std::vector<boost::thread> g_threads;

void merge_tasks (oid_t dep);

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
        SharedMutex::SharedLock lock(g_merge_mutex);
        Task task;
        if (m_queue.try_pop(task)) {
            execute(task);
            return true;
        } else {
            return false;
        }
    }

    void merge (oid_t dep)
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
            SharedMutex::UniqueLock lock(g_merge_mutex);
            execute(task);
            merge_tasks(task.dep);
            return true;
        } else {
            return false;
        }
    }
};

static TaskQueue<MergeTask> g_mergers;
static TaskQueue<CleanupTask> g_cleanups;
static TaskQueue<PositiveOrderTask> g_positive_orders;
static TaskQueue<NegativeOrderTask> g_negative_orders;
static TaskQueue<NullaryFunctionTask> g_nullary_functions;
static TaskQueue<InjectiveFunctionTask> g_injective_functions;
static TaskQueue<BinaryFunctionTask> g_binary_functions;
static TaskQueue<SymmetricFunctionTask> g_symmetric_functions;


inline bool try_work ()
{
    return g_mergers.try_execute()
        or g_nullary_functions.try_execute()
        or g_injective_functions.try_execute()
        or g_binary_functions.try_execute()
        or g_symmetric_functions.try_execute()
        or g_positive_orders.try_execute()
        or g_negative_orders.try_execute()
        or g_cleanups.try_execute();
}

inline void merge_tasks (oid_t dep)
{
    g_nullary_functions.merge(dep);
    g_injective_functions.merge(dep);
    g_binary_functions.merge(dep);
    g_symmetric_functions.merge(dep);
    g_positive_orders.merge(dep);
    g_negative_orders.merge(dep);
}

void do_work ()
{
    const auto timeout = boost::posix_time::seconds(60);
    while (g_alive) {
        if (not try_work()) {
            boost::unique_lock<boost::mutex> lock(g_work_mutex);
            g_work_condition.timed_wait(lock, timeout);
        }
    }
}

void start (size_t thread_count)
{
    g_alive = true;
    for (size_t i = 0; i < thread_count; ++i) {
        g_threads.push_back(boost::thread(do_work));
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
