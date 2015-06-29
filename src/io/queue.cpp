#include <pomagma/io/queue.hpp>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define POMAGMA_ASSERT_C(expr) POMAGMA_ASSERT((expr) != -1, strerror(errno))

namespace pomagma {

//----------------------------------------------------------------------------
// FileBackedQueue

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

void FileBackedQueue::push (const void * message, uint8_t size)
{
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);
    POMAGMA_ASSERT_C(pwrite(m_fid, &size, 1, m_write_offset));
    m_write_offset += 1;
    POMAGMA_ASSERT_C(pwrite(m_fid, message, size, m_write_offset));
    m_write_offset += size;
}

uint8_t FileBackedQueue::try_pop (void * message)
{
    std::unique_lock<std::mutex> lock(m_mutex);
    if (unlikely(m_read_offset == m_write_offset)) {
        if (m_read_offset) {
            m_write_offset = 0;
            m_read_offset = 0;
            POMAGMA_ASSERT_C(ftruncate(m_fid, 0));
        }
        return 0;
    }
    uint8_t size;
    POMAGMA_ASSERT_C(pread(m_fid, &size, 1, m_read_offset));
    m_read_offset += 1;
    POMAGMA_ASSERT_C(pread(m_fid, message, size, m_read_offset));
    m_read_offset += size;
    return size;
}

//----------------------------------------------------------------------------
// PagedQueue

inline void PagedQueue::unsafe_grow ()
{
    if (m_blocks.size() < m_write_offset / Block::capacity + 1) {
        void * message;
        int info = posix_memalign(& message, Block::capacity, Block::capacity);
        POMAGMA_ASSERT(info == 0, "out of memory");
        m_blocks.push_back({static_cast<char *>(message), Block::capacity});
    }
}

inline void PagedQueue::unsafe_clear ()
{
    for (auto & block : m_blocks) {
        block.size = 0;
    }
}

PagedQueue::PagedQueue ()
    : m_blocks(),
      m_write_offset(0),
      m_read_offset(0)
{
    m_blocks.reserve(BYTES_PER_CACHE_LINE / sizeof(Block));
    unsafe_grow();
}

PagedQueue::~PagedQueue ()
{
    for (auto & block : m_blocks) { free(block.data); }
}

void PagedQueue::push (const void * message, uint8_t size)
{
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);

    size_t offset = m_write_offset % Block::capacity;
    if (unlikely(offset + 1 + size > Block::capacity)) {
        m_write_offset = next_block(m_write_offset);
        unsafe_grow();
        offset = 0;
    }
    Block & block = m_blocks[m_write_offset / Block::capacity];
    memcpy(block.data + offset, & size, 1);
    memcpy(block.data + offset + 1, message, size);
    block.size += 1 + size;
    m_write_offset += 1 + size;
}

uint8_t PagedQueue::try_pop (void * message)
{
    std::unique_lock<std::mutex> lock(m_mutex);

    if (unlikely(m_read_offset == m_write_offset)) { // queue is empty
        if (m_read_offset != 0) {
            m_write_offset = 0;
            m_read_offset = 0;
            unsafe_clear();
        }
        return 0;
    }
    size_t offset = m_read_offset % Block::capacity;
    Block & block = m_blocks[m_read_offset / Block::capacity];
    uint8_t size;
    memcpy(& size, block.data + offset, 1);
    memcpy(message, block.data + offset + 1, size);
    if (likely(offset + 1 != block.size)) {
        m_read_offset += 1 + size;
    } else {
        m_read_offset = next_block(m_read_offset);
    }

    return size;
}

} // namespace pomagma
