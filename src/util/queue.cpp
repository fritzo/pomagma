#include <pomagma/util/queue.hpp>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define POMAGMA_ASSERT_C(expr) POMAGMA_ASSERT((expr) != -1, strerror(errno))

namespace pomagma {

//----------------------------------------------------------------------------
// VectorQueue

void VectorQueue::push(const void* message, uint8_t size) {
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);
    size_t offset = m_data.size();
    m_data.resize(offset + 1 + size);
    memcpy(m_data.data() + offset, &size, 1);
    memcpy(m_data.data() + offset + 1, message, size);
}

uint8_t VectorQueue::try_pop(void* message) {
    std::unique_lock<std::mutex> lock(m_mutex);
    uint8_t size = 0;
    if (likely(m_read_offset != m_data.size())) {
        memcpy(&size, m_data.data() + m_read_offset, 1);
        memcpy(message, m_data.data() + m_read_offset + 1, size);
        m_read_offset += 1 + size;
        return size;
    } else if (m_read_offset) {
        m_read_offset = 0;
        m_data.clear();
    }
    return size;
}

//----------------------------------------------------------------------------
// FileBackedQueue

inline int create_inaccessible_temp_file() {
    auto path = fs::unique_path("/tmp/pomagma.queue.%%%%%%%%%%%%%%%%%%%%");
    int fid = open(path.c_str(), O_CREAT | O_TRUNC | O_RDWR, S_IRUSR | S_IWUSR);
    unlink(path.c_str());
    return fid;
}

FileBackedQueue::FileBackedQueue()
    : m_write_offset(0),
      m_read_offset(0),
      m_fid(create_inaccessible_temp_file()) {
    POMAGMA_ASSERT_C(m_fid);
}

void FileBackedQueue::push(const void* message, uint8_t size) {
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);
    POMAGMA_ASSERT_C(pwrite(m_fid, &size, 1, m_write_offset));
    m_write_offset += 1;
    POMAGMA_ASSERT_C(pwrite(m_fid, message, size, m_write_offset));
    m_write_offset += size;
}

uint8_t FileBackedQueue::try_pop(void* message) {
    std::unique_lock<std::mutex> lock(m_mutex);
    uint8_t size = 0;
    if (likely(m_read_offset != m_write_offset)) {
        POMAGMA_ASSERT_C(pread(m_fid, &size, 1, m_read_offset));
        m_read_offset += 1;
        POMAGMA_ASSERT_C(pread(m_fid, message, size, m_read_offset));
        m_read_offset += size;
    } else if (m_read_offset) {
        m_write_offset = 0;
        m_read_offset = 0;
        POMAGMA_ASSERT_C(ftruncate(m_fid, 0));
    }
    return size;
}

}  // namespace pomagma
