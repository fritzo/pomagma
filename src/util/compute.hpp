#include <pomagma/util/thraeding.hpp>
#include <pomagma/util/util.hpp>
#include <stxxl/queue>
#include <tbb/cache_aligned_allocator.h>
#include <tbb/concurrent_queue.h>
#include <type_traits>
#include <unordered_set>
#include <vector>

namespace pomagma {
namespace compute {

typedef uint32_t Id;  // zero value is reserved for NULL
struct trivial_hash { size_t operator() (const Id & id) const { return id; } };

template<class T, size_t alignment = 64>
class Padded : public T
{
    char m_padding[(alignment - (sizeof(T) % alignment)) % alignment];

public:

    Padded ()
    {
        static_assert(sizeof(Padded<T>) % alignment == 0, "false sharing");
        static_assert(sizeof(Padded<T>) < sizeof(T) + alignment, "overpadded");
    }
};

template<class T>
class SharedVector :
    public std::vector<Padded<T>, tbb::cache_aligned_allocator<Padded<T>>>
{
};

class StxxlQueue
{
    enum { stxxl_block_size = 32768 };
    stxxl::queue<std::string, stxxl_block_size> m_queue;
    std::mutex m_mutex;

public:

    ~StxxlQueue ()
    {
        POMAGMA_ASSERT(m_queue.empty(), m_queue.size() << " tasks lost");
    }

    void push (const std::string & message)
    {
        std::unique_lock<std::mutex> lock(m_mutex);
        m_queue.push(std::string());
        Task.dump(m_queue.back());
    }

    bool try_pop (std::string & message)
    {
        std::unique_lock<std::mutex> lock(m_mutex);
        bool found = not m_queue.empty();
        if (likely(found)) {
            message = std::move(m_queue.front());
            m_queue.pop();
        }
        return found;
    }
};

class TbbQueue
{
    tbb::concurrent_queue<std::string> m_queue;

public:

    ~TbbQueue ()
    {
        POMAGMA_ASSERT(m_queue.empty(), m_queue.size() << " tasks lost");
    }

    void push (const std::string & message) { m_queue.push(message); }
    bool try_pop (std::string & message) { return m_queue.try_pop(message); }
};

class TaskBase
{
public:

    virtual void dump (std::string & destin) = 0;
    virtual void load (const std::string & source) = 0;
};

class CellBase : noncopyable
{
public:

    virtual void load () = 0;
    virtual void dump () = 0;
};

template<class Cell, class Queue>
struct CellWithQueue
{
    Queue queue;
    Cell cell;
} __attribute__((aligned(BYTES_PER_CACHE_LINE)));

template<class Cell, class Queue, class Task>
class Scheduler
{
    std::vector<Cell *> m_cells;
    SharedVector<Queue> m_queues;
    std::vector<std::atomic<uint32_t>> m_queue_sizes;
    std::unordered_set<Id, trivial_hash> m_active_cells;
    std::mutex m_mutex;
    std::atomic<bool> m_processing;

public:

    Scheduler () :
        m_cells(1, nullptr),
        m_queues(1),
        m_queue_sizes(1, 0),
        m_ative_cells(),
        m_mutex(),
        m_processing(false)
    {
        static_assert(std::is_base_of(CellBase, Cell)::value, "concept error");
        static_assert(std::is_base_of(TaskBase, Task)::value, "concept error");
    }

    ~Scheduler () { for (auto ptr : m_cells) { delete ptr; } }

    Id add_cell (Cell * cell)
    {
        POMAGMA_ASSERT(not m_processing, "called add_cell while processing");
        POMAGMA_ASSERT_ALIGNED_(1, cell);
        m_cells.push_back(cell);
        m_queues.resize(m_cells.size());
        m_queue_sizes.push_back(0);
        return m_cells.size() - 1;
    }

    void process ()
    {
        POMAGMA_ASSERT(not m_processing.fetch_or(true), "called process twice");
        #pragma omp parallel
        {
            Id cell_id = 0;
            while (cell_id = try_switch_cell(cell_id)) {
                Cell & cell = * m_cells[cell_id];
                Queue & queue = m_queues[cell_id];
                auto & queue_size = m_queue_sizes[cell_id];
                cell.load();
                Task task;
                while (queue.try_pop(recv(cell_id, task))) {
                    queue_size.fetch_sub(1U, acq_rel);
                    execute(task, cell);
                }
                cell.dump();
                // FIXME it is possible for all but one thread to exit early
            }
        }
        m_processing.store(false);
    }

protected:

    virtual void execute (const Task & task, Cell & cell) = 0;

    // this is called during execute();
    void send (Id cell_id, const Task & task)
    {
        m_queues[cell_id].push(task);
        m_queue_sizes[cell_id].fetch_add(1U, acq_rel);
    }

private:

    Id try_switch_cell (Id prev_id)
    {
        std::unique_lock<std::mutex> lock(m_mutex);
        if (likely(prev_id)) {
            m_active_cells.erase(prev_id);
        }
        size_t best_count = 0;
        size_t best_id = 0;
        for (size_t id = 1, end = m_cells.size(); id != end; ++id) {
            size_t count = m_queue_sizes[id].load(acquire);
            if (unlikely(count > best_count)) {
                if (m_active_cells.find(id) == m_active_cells.end()) {
                    best_count = count;
                    best_id = id;
                }
            }
        }
        return best_id;  // possibly zero
    }
};

} // namespace compute
} // namespace pomagma
