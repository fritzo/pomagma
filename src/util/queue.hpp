#pragma once

#include <deque>
#include <mutex>
#include <pomagma/util/util.hpp>
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

} // namespace pomagma
