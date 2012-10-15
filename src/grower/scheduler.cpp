#include "scheduler.hpp"
#include "threading.hpp"
#include <vector>
#include <thread>
#include <chrono>
#include <tbb/concurrent_queue.h>


namespace pomagma
{

namespace Scheduler
{

static const size_t DEFAULT_THREAD_COUNT = 1;

static size_t g_worker_count = DEFAULT_THREAD_COUNT;
static size_t g_cleanup_count = DEFAULT_THREAD_COUNT;
static size_t g_diffuse_count = DEFAULT_THREAD_COUNT;

static std::atomic<bool> g_alive(false);
static std::atomic<uint_fast64_t> g_merge_count(0);
static std::atomic<uint_fast64_t> g_enforce_count(0);
static std::mutex g_work_mutex;
static SharedMutex g_strict_mutex;
static std::vector<std::thread> g_threads;


bool is_alive ()
{
    return g_alive.load();
}

void set_thread_counts (
        size_t worker_threads,
        size_t cleanup_threads,
        size_t diffuse_threads)
{
    POMAGMA_ASSERT_LE(1, worker_threads);
    POMAGMA_ASSERT_LE(1, cleanup_threads);
    POMAGMA_ASSERT_LE(1, diffuse_threads);

    g_worker_count = worker_threads;
    g_cleanup_count = cleanup_threads;
    g_diffuse_count = diffuse_threads;
}

template<class Task>
class TaskQueue
{
    tbb::concurrent_queue<Task> m_queue;

public:

    void push (const Task & task)
    {
        m_queue.push(task);
    }

    bool try_execute ()
    {
        SharedMutex::SharedLock lock(g_strict_mutex);
        Task task;
        if (m_queue.try_pop(task)) {
            execute(task);
            g_enforce_count.fetch_add(1, relaxed);
            return true;
        } else {
            return false;
        }
    }

    void cancel_referencing (Ob ob)
    {
        tbb::concurrent_queue<Task> queue;
        std::swap(queue, m_queue);
        for (Task task; queue.try_pop(task);) {
            if (not task.references(ob)) {
                push(task);
            }
        }
    }
};

void cancel_tasks_referencing (Ob ob);

template<>
class TaskQueue<MergeTask>
{
    tbb::concurrent_queue<MergeTask> m_queue;

public:

    void push (const MergeTask & task)
    {
        m_queue.push(task);
    }

    bool try_execute ()
    {
        MergeTask task;
        // XXX TODO this is unsafe in presence of insert,remove tasks
        if (m_queue.try_pop(task)) {
            SharedMutex::UniqueLock lock(g_strict_mutex);
            execute(task);
            g_merge_count.fetch_add(1, relaxed);
            cancel_tasks_referencing(task.dep);
            return true;
        } else {
            return false;
        }
    }
};


static TaskQueue<MergeTask> g_merge_tasks;
static TaskQueue<ExistsTask> g_exists_tasks;
static TaskQueue<PositiveOrderTask> g_positive_order_tasks;
static TaskQueue<NegativeOrderTask> g_negative_order_tasks;
static TaskQueue<NullaryFunctionTask> g_nullary_function_tasks;
static TaskQueue<InjectiveFunctionTask> g_injective_function_tasks;
static TaskQueue<BinaryFunctionTask> g_binary_function_tasks;
static TaskQueue<SymmetricFunctionTask> g_symmetric_function_tasks;

inline void cancel_tasks_referencing (Ob ob)
{
    g_exists_tasks.cancel_referencing(ob);
    g_nullary_function_tasks.cancel_referencing(ob);
    g_injective_function_tasks.cancel_referencing(ob);
    g_binary_function_tasks.cancel_referencing(ob);
    g_symmetric_function_tasks.cancel_referencing(ob);
    g_positive_order_tasks.cancel_referencing(ob);
    g_negative_order_tasks.cancel_referencing(ob);
}

void do_work ()
{
    while (g_alive.load()) {
        /* TODO
        if (try_to_merge()) return;
        if (try_to_enforce()) return;
        lock_guard(global strict mutex);
        // henceforth no new merge tasks can be scheduled
        if (merges_pending()) return;
        */

        if (g_merge_tasks.try_execute()) return;

        if (g_exists_tasks.try_execute() or
            g_nullary_function_tasks.try_execute() or
            g_injective_function_tasks.try_execute() or
            g_binary_function_tasks.try_execute() or
            g_symmetric_function_tasks.try_execute() or
            g_positive_order_tasks.try_execute() or
            g_negative_order_tasks.try_execute()) return;

        // XXX this is not sufficiently safe; instead:
        // lock global mutex
        // check again for merge tasks
        if (Ob removed = execute(SampleTask())) {
            // XXX this is not safe; instead lock the global mutex
            // around execution of SampleTask and cancellation
            cancel_tasks_referencing(removed);
        }
    }
}

void do_cleanup ()
{
    while (g_alive.load()) {
        SharedMutex::SharedLock lock(g_strict_mutex);
        execute(CleanupTask());
    }
}

void do_diffuse ()
{
    while (g_alive.load()) {
        SharedMutex::SharedLock lock(g_strict_mutex);
        execute(DiffuseTask());
    }
}

void start ()
{
    POMAGMA_INFO("starting grower");

    bool was_alive = false;
    POMAGMA_ASSERT(g_alive.compare_exchange_strong(was_alive, true),
            "started scheduler twice");

    g_merge_count = 0;
    g_enforce_count = 0;

    POMAGMA_INFO("starting " << g_worker_count << " worker threads");
    for (size_t i = 0; i < g_worker_count; ++i) {
        g_threads.push_back(std::thread(do_work));
    }

    POMAGMA_INFO("starting " << g_cleanup_count << " cleanup threads");
    for (size_t i = 0; i < g_cleanup_count; ++i) {
        g_threads.push_back(std::thread(do_cleanup));
    }

    POMAGMA_INFO("starting " << g_diffuse_count << " diffuse threads");
    for (size_t i = 0; i < g_diffuse_count; ++i) {
        g_threads.push_back(std::thread(do_diffuse));
    }
}

void stop ()
{
    POMAGMA_INFO("stopping grower");

    bool was_alive = true;
    POMAGMA_ASSERT(g_alive.compare_exchange_strong(was_alive, false),
            "started scheduler twice");

    POMAGMA_INFO("stopping " << g_threads.size() << " threads");
    while (not g_threads.empty()) {
        g_threads.back().join();
        g_threads.pop_back();
    }

    POMAGMA_INFO("processed " << g_merge_count.load() << " merge tasks");
    POMAGMA_INFO("processed " << g_enforce_count.load() << " enforce tasks");
}

} // namespace Scheduler


void schedule (const MergeTask & task)
{
    Scheduler::g_merge_tasks.push(task);
}

void schedule (const ExistsTask & task)
{
    Scheduler::g_exists_tasks.push(task);
}

void schedule (const PositiveOrderTask & task)
{
    Scheduler::g_positive_order_tasks.push(task);
}

void schedule (const NegativeOrderTask & task)
{
    Scheduler::g_negative_order_tasks.push(task);
}

void schedule (const NullaryFunctionTask & task)
{
    Scheduler::g_nullary_function_tasks.push(task);
}

void schedule (const InjectiveFunctionTask & task)
{
    Scheduler::g_injective_function_tasks.push(task);
}

void schedule (const BinaryFunctionTask & task)
{
    Scheduler::g_binary_function_tasks.push(task);
}

void schedule (const SymmetricFunctionTask & task)
{
    Scheduler::g_symmetric_function_tasks.push(task);
}

} // namespace pomagma
