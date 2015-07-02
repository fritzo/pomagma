#pragma once

#include <deque>
#include <mutex>
#include <pomagma/util/util.hpp>
#include <pomagma/util/aligned_alloc.hpp>
#include <tbb/cache_aligned_allocator.h>
#include <vector>

namespace pomagma {

// A multi-producer single-consumer queue for variable-sized messages.
class SharedQueue : noncopyable
{
public:

    enum { max_message_size = 256 };

    virtual ~SharedQueue () {}

    // these should be thread safe for multiple producers and a single consumer
    virtual void push (const void * data, uint8_t size) = 0;
    virtual uint8_t try_pop (void * data) = 0;
};

class VectorQueue : public SharedQueue
{
public:

    VectorQueue () : m_read_offset(0) { m_data.reserve(4096); }
    virtual ~VectorQueue () {}

    // these are thread safe for multiple producers and multiple consumers
    virtual void push (const void * message, uint8_t size);
    virtual uint8_t try_pop (void * message);

private:

    std::mutex m_mutex;
    std::vector<char, tbb::cache_aligned_allocator<char>> m_data;
    size_t m_read_offset;
};

class FileBackedQueue : public SharedQueue
{
public:

    FileBackedQueue (const std::string & path);
    virtual ~FileBackedQueue ();

    // these are thread safe for multiple producers and multiple consumers
    virtual void push (const void * message, uint8_t size);
    virtual uint8_t try_pop (void * message);

private:

    std::mutex m_mutex;
    size_t m_write_offset;
    size_t m_read_offset;
    const int m_fid;
    const std::string m_path;
};

// FIXME this is broken
class PagedQueue : public SharedQueue
{
public:

    PagedQueue ();
    virtual ~PagedQueue ();

    // these are thread safe for multiple producers and multiple consumers
    virtual void push (const void * message, uint8_t size);
    virtual uint8_t try_pop (void * message);

private:

    void _validate() const;
    void validate () const { if (POMAGMA_DEBUG_LEVEL) { _validate(); } }

    void push_page ();
    void pop_page ();

    struct Page
    {
        static constexpr size_t capacity () { return 4096UL; }
        char * data;
        size_t size;
    };

    std::mutex m_mutex;
    std::deque<Page, tbb::cache_aligned_allocator<Page>> m_pages;
    size_t m_write_offset;
    size_t m_read_offset;
};

template<class Queue>
class SharedBroker
{
    Padded<Queue> * const m_queues;
    const size_t m_queue_count;

public:

    explicit SharedBroker (size_t queue_count)
        : m_queues(alloc_blocks<Padded<Queue>>(queue_count)),
          m_queue_count(queue_count)
    {
        for (size_t i = 0; i < m_queue_count; ++i) {
            new(m_queues + i) Padded<Queue>();
        }
    }

    ~SharedBroker ()
    {
        for (size_t i = 0; i < m_queue_count; ++i) {
            m_queues[i].~Padded<Queue>();
        }
    }

    void push (size_t queue_id, const void * message, uint8_t size)
    {
        POMAGMA_ASSERT1(queue_id < m_queue_count, "bad queue_id: " << queue_id);
        m_queues[queue_id].push(message, size);
    }

    uint8_t try_pop (size_t queue_id, void * message)
    {
        POMAGMA_ASSERT1(queue_id < m_queue_count, "bad queue_id: " << queue_id);
        return m_queues[queue_id].try_pop(message);
    }
};

} // namespace pomagma
