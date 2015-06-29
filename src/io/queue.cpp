#include <pomagma/io/queue.hpp>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define POMAGMA_ASSERT_C(expr) POMAGMA_ASSERT((expr) != -1, strerror(errno))

namespace pomagma {

FileBackedQueue::FileBackedQueue (const std::string & path)
    : m_write_offset(0),
      m_read_offset(0),
      m_fid(open(path.c_str(), O_CREAT | O_TRUNC | O_RDWR, S_IRUSR | S_IWUSR)),
      m_path(path)
{
    POMAGMA_ASSERT_C(m_fid);
}

FileBackedQueue::~FileBackedQueue ()
{
    unlink(m_path.c_str()); // ignore errors
}

void FileBackedQueue::push (const void * data, uint8_t size)
{
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);
    POMAGMA_ASSERT_C(pwrite(m_fid, &size, 1, m_write_offset));
    m_write_offset += 1;
    POMAGMA_ASSERT_C(pwrite(m_fid, data, size, m_write_offset));
    m_write_offset += size;
}

uint8_t FileBackedQueue::try_pop (void * data)
{
    std::unique_lock<std::mutex> lock(m_mutex);
    if (unlikely(m_read_offset == m_write_offset)) {
        if (m_read_offset) {
            m_write_offset = 0;
            m_read_offset = 0;
            POMAGMA_ASSERT_C(ftruncate(m_fid, 0));
        }
        return false;
    }
    uint8_t size;
    POMAGMA_ASSERT_C(pread(m_fid, &size, 1, m_read_offset));
    m_read_offset += 1;
    POMAGMA_ASSERT_C(pread(m_fid, data, size, m_read_offset));
    m_read_offset += size;
    return size;
}

} // namespace pomagma
