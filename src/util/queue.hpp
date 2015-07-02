#pragma once

#include <pomagma/util/util.hpp>
#include <tbb/cache_aligned_allocator.h>
#include <vector>
#include <mutex>

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

    void unsafe_grow ();
    void unsafe_clear ();

    struct Block
    {
        enum { capacity = 4096 };
        char * data;
        size_t size;
    };

    static size_t next_block (size_t offset)
    {
        const size_t mask = ~static_cast<size_t>(Block::capacity - 1);
        return (offset + Block::capacity) & mask;
    }

    std::mutex m_mutex;
    std::vector<Block, tbb::cache_aligned_allocator<Block>> m_blocks;
    size_t m_write_offset;
    size_t m_read_offset;
};

} // namespace pomagma
