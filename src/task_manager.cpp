#include "task_manager.hpp"
#include <vector>
#include <atomic>
#include <boost/thread/thread.hpp>
#include <boost/thread/mutex.hpp>
#include <boost/thread/shared_mutex.hpp>
#include <boost/thread/locks.hpp>
#include <boost/thread/condition_variable.hpp>
#include <tbb/concurrent_queue.h>

#define POMAGMA_ASSERT_MERGE(POMAGMA_dep, POMAGMA_rep)\
    POMAGMA_ASSERT3(dep < rep,\
            "out of order merge: " << (dep) << ", " << (rep))


namespace pomagma
{

//----------------------------------------------------------------------------
// merging

inline bool merge (EquationTask & task, oid_t dep, oid_t rep)
{
    if (task.dep == dep) {
        return false; // assume "rep = m_rep" is already enqueued
    } else {
        if (task.rep == dep) {
            task.rep = rep;
        }
        return true;
    }
}

inline bool merge (NullaryFunctionTask &, oid_t, oid_t)
{
    return true;
}

inline bool merge (UnaryFunctionTask & task, oid_t dep, oid_t)
{
    return task.arg != dep;
}

inline bool merge (BinaryFunctionTask & task, oid_t dep, oid_t)
{
    return task.lhs != dep and task.lhs != dep;
}

inline bool merge (SymmetricFunctionTask & task, oid_t dep, oid_t)
{
    return task.lhs != dep and task.lhs != dep;
}

inline bool merge (PositiveRelationTask & task, oid_t dep, oid_t)
{
    return task.lhs != dep and task.lhs != dep;
}

inline bool merge (NegativeRelationTask & task, oid_t dep, oid_t)
{
    return task.lhs != dep and task.lhs != dep;
}

//----------------------------------------------------------------------------
// task queuing

template<class Task>
class TaskQueue
{
    typedef tbb::concurrent_queue<Task> Queue;
    Queue m_queue;
    boost::shared_mutex m_mutex;

public:

    void push (const Task & task)
    {
        boost::shared_lock<boost::shared_mutex> lock(m_mutex);
        m_queue.push(task);
    }

    bool try_pop (Task & task)
    {
        boost::shared_lock<boost::shared_mutex> lock(m_mutex);
        return m_queue.try_pop(task);
    }

    bool try_execute ()
    {
        Task task;
        if (try_pop(task)) {
            execute(task);
            return true;
        } else {
            return false;
        }
    }

    void merge (oid_t dep, oid_t rep)
    {
        boost::unique_lock<boost::shared_mutex> lock(m_mutex);

        Queue queue;
        std::swap(queue, m_queue);
        for (Task task; queue.try_pop(task);) {
            if (merge(task, dep, rep)) {
                push(task);
            }
        }
    }
};

//----------------------------------------------------------------------------
// task manager

namespace TaskManager
{

namespace // anonymous
{

static TaskQueue<EquationTask> g_equations;
static TaskQueue<NullaryFunctionTask> g_nullary_functions;
static TaskQueue<UnaryFunctionTask> g_unary_functions;
static TaskQueue<BinaryFunctionTask> g_binary_functions;
static TaskQueue<SymmetricFunctionTask> g_symmetric_functions;
static TaskQueue<PositiveRelationTask> g_positive_relations;
static TaskQueue<NegativeRelationTask> g_negative_relations;

static std::atomic<bool> g_alive(false);
static std::atomic<uint_fast64_t> g_merge_count(0);
static std::atomic<uint_fast64_t> g_enforce_count(0);

static boost::mutex g_mutex;
static boost::condition_variable g_condition;
static std::vector<boost::thread> g_threads;

inline bool try_work ()
{
    return g_equations.try_execute()
        or g_nullary_functions.try_execute()
        or g_unary_functions.try_execute()
        or g_binary_functions.try_execute()
        or g_symmetric_functions.try_execute()
        or g_positive_relations.try_execute()
        or g_negative_relations.try_execute();
}

void do_work ()
{
    while (g_alive) {
        if (not try_work()) {
            boost::unique_lock<boost::mutex> lock(g_mutex);
            g_condition.wait(lock);
        }
    }
}

} // anonymous namespace

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
    g_condition.notify_all();
    while (not g_threads.empty()) {
        g_threads.back().join();
        g_threads.pop_back();
    }
}

} // namespace TaskManager


void enqueue (const EquationTask & task)
{
    TaskManager::g_equations.push(task);
}

void enqueue (const NullaryFunctionTask & task)
{
    TaskManager::g_nullary_functions.push(task);
}

void enqueue (const UnaryFunctionTask & task)
{
    TaskManager::g_unary_functions.push(task);
}

void enqueue (const BinaryFunctionTask & task)
{
    TaskManager::g_binary_functions.push(task);
}

void enqueue (const SymmetricFunctionTask & task)
{
    TaskManager::g_symmetric_functions.push(task);
}

void enqueue (const PositiveRelationTask & task)
{
    TaskManager::g_positive_relations.push(task);
}

void enqueue (const NegativeRelationTask & task)
{
    TaskManager::g_negative_relations.push(task);
}

} // namespace pomagma
