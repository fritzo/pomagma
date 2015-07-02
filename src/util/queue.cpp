#include <pomagma/util/queue.hpp>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define POMAGMA_ASSERT_C(expr) POMAGMA_ASSERT((expr) != -1, strerror(errno))

namespace pomagma {

//----------------------------------------------------------------------------
// VectorQueue

void VectorQueue::push (const void * message, uint8_t size)
{
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);
    size_t offset = m_data.size();
    m_data.resize(offset + 1 + size);
    memcpy(m_data.data() + offset, & size, 1);
    memcpy(m_data.data() + offset + 1, message, size);
}

uint8_t VectorQueue::try_pop (void * message)
{
    std::unique_lock<std::mutex> lock(m_mutex);
    if (likely(m_read_offset != m_data.size())) {
        uint8_t size;
        memcpy(& size, m_data.data() + m_read_offset, 1);
        memcpy(message, m_data.data() + m_read_offset + 1, size);
        m_read_offset += 1 + size;
        return size;
    } else {
        return 0;
    }
}

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

void PagedQueue::_validate () const
{
    POMAGMA_ASSERT_LE(m_read_offset, m_write_offset);
    POMAGMA_ASSERT_LT(m_read_offset, Page::capacity());
    POMAGMA_ASSERT_LE(m_write_offset, Page::capacity() * m_pages.size());
    if (size_t write_offset = m_write_offset % Page::capacity()) {
        POMAGMA_ASSERT(not m_pages.empty(), "page missing");
        POMAGMA_ASSERT_EQ(write_offset, m_pages.back().size);
    }
    for (const Page & page: m_pages) {
        POMAGMA_ASSERT(page.data, "data is null");
        POMAGMA_ASSERT_LE(page.size, Page::capacity());

        size_t size = 0;
        while (size < page.size) {
            uint8_t message_size;
            memcpy(& message_size, page.data + size, 1);
            size += 1 + message_size;
        }
        POMAGMA_ASSERT_EQ(size, page.size);
    }
}

inline void PagedQueue::push_page ()
{
    void * data = nullptr;
    int info = posix_memalign(& data, Page::capacity(), Page::capacity());
    POMAGMA_ASSERT(info == 0, "out of memory");
    m_pages.push_back({static_cast<char *>(data), 0});
}

inline void PagedQueue::pop_page ()
{
    POMAGMA_ASSERT1(not m_pages.empty(), "no pages to pop");
    free(m_pages.front().data);
    m_pages.pop_front();
    m_write_offset -= Page::capacity();
    m_read_offset = 0;
}

PagedQueue::PagedQueue ()
    : m_pages(),
      m_write_offset(0),
      m_read_offset(0)
{
    static_assert(Page::capacity() >= 1 + sizeof(uint8_t),
        "pages are too small");
    validate();
}

PagedQueue::~PagedQueue ()
{
    validate();
    POMAGMA_ASSERT1(m_read_offset == m_write_offset,
        "queue not empty at destruction");
    for (Page & page : m_pages) { free(page.data); }
}

void PagedQueue::push (const void * message, uint8_t size)
{
    POMAGMA_ASSERT1(size, "empty messages are not allowed");
    std::unique_lock<std::mutex> lock(m_mutex);

    validate();
    size_t offset = m_write_offset % Page::capacity();
    if (unlikely(offset + 1UL + size > Page::capacity())) { // would span page
        m_write_offset = (m_write_offset ^ offset) + Page::capacity();
        offset = 0;
    }
    if (offset == 0) {
        push_page();
    }
    Page & page = m_pages.back();
    memcpy(page.data + offset, & size, 1);
    memcpy(page.data + offset + 1, message, size);
    page.size += 1UL + size;
    m_write_offset += 1UL + size;
    validate();
}

uint8_t PagedQueue::try_pop (void * message)
{
    std::unique_lock<std::mutex> lock(m_mutex);

    validate();
    size_t offset = m_read_offset;
    if (unlikely(offset == m_write_offset)) { // queue is empty
        return 0;
    } else {
        const Page & page = m_pages.front();
        uint8_t size;
        memcpy(& size, page.data + offset, 1);
        memcpy(message, page.data + offset + 1, size);
        m_read_offset += 1UL + size;
        if (unlikely(m_read_offset == page.size)) {
            if (m_read_offset != m_write_offset) {
                pop_page();
            }
        }
        return size;
    }
    validate();
}

} // namespace pomagma
