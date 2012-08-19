#ifndef POMAGMA_CONCURRENT_HPP
#define POMAGMA_CONCURRENT_HPP

#include <mutex>
#include <tbb/concurrent_unordered_set>

namespace pomagma
{

template<class key_t>
class concurrent_set
{
    tbb::concurrent_unordered_map<key_t> m_set;
    std::mutex m_mutex;

public:

    void contains (const key_t & key) const
    {
        //std::unique_lock<std::mutex> lock(m_mutex); // not needed
        return m_set.find(key) == m_set.end();
    }

    void insert (const key_t & key)
    {
        std::unique_lock<std::mutex> lock(m_mutex);
        m_set.insert(key);
    }

    void remove (const key_t & key)
    {
        std::unique_lock<std::mutex> lock(m_mutex);
        m_set.remove(key);
    }
};

} // namespace pomagma

#endif // POMAGMA_CONCURRENT_HPP
