#pragma once

#include <pomagma/util/util.hpp>
#include <mutex>

namespace pomagma {

// A multi-producer multi-consumer variable-sized-message queue.
class FileBackedQueue : noncopyable
{
public:

    enum { max_message_size = 256 };

    FileBackedQueue (const std::string & path);
    ~FileBackedQueue ();

    // these are thread safe for multiple producers and multiple consumers
    void push (const void * data, uint8_t size);
    uint8_t try_pop (void * data);

private:

    std::mutex m_mutex;
    size_t m_write_offset;
    size_t m_read_offset;
    const int m_fid;
    const std::string m_path;
};

} // namespace pomagma
