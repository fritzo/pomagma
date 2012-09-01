#ifndef POMAGMA_THREADING_HPP
#define POMAGMA_THREADING_HPP

#include "util.hpp"
#include <mutex>
#include <atomic>
#include <pthread.h>

namespace pomagma
{

template<class Mutex>
struct unique_lock
{
    Mutex & m_mutex;
public:
    unique_lock (Mutex & mutex) : m_mutex(mutex) { mutex.lock(); }
    ~unique_lock () { m_mutex.unlock(); }
};

template<class Mutex>
struct shared_lock
{
    Mutex & m_mutex;
public:
    shared_lock (Mutex & mutex) : m_mutex(mutex) { m_mutex.lock_shared(); }
    ~shared_lock () { m_mutex.unlock_shared(); }
};



class Mutex
{
    std::mutex m_mutex;
public:
    void lock () { m_mutex.lock(); }
    void unlock () { m_mutex.unlock(); }
    typedef unique_lock<Mutex> Lock;
};



#if (POMAGMA_DEBUG_LEVEL == 0)

struct AssertMutex
{
    void lock () {}
    void unlock () {}
    struct Lock { Lock (AssertMutex &) {} };
};

#else // (POMAGMA_DEBUG_LEVEL == 0)

class AssertMutex
{
    std::atomic<bool> m_flag;

public:

    AssertMutex () : m_flag(false) {}

    bool is_locked () const { return m_flag; }

    void lock ()
    {
        bool expected = false;
        POMAGMA_ASSERT(m_flag.compare_exchange_strong(expected, true),
                "lock contention");
    }

    void unlock ()
    {
        bool expected = true;
        POMAGMA_ASSERT(m_flag.compare_exchange_strong(expected, false),
                "unlock contention");
    }

    typedef unique_lock<Mutex> Lock;
};

#endif // (POMAGMA_DEBUG_LEVEL == 0)



// this wraps pthread_wrlock, which is smaller & faster than boost::shared_mutex.
//
// adapted from:
// http://boost.2283326.n4.nabble.com/boost-shared-mutex-performance-td2659061.html
class SharedMutex
{
    pthread_rwlock_t m_rwlock;

public:

    SharedMutex ()
    {
        int status = pthread_rwlock_init(&m_rwlock, NULL);
        POMAGMA_ASSERT1(status == 0, "pthread_rwlock_init failed");
    }

    ~SharedMutex ()
    {
        int status = pthread_rwlock_destroy(&m_rwlock);
        POMAGMA_ASSERT1(status == 0, "pthread_rwlock_destroy failed");
    }

    void lock ()
    {
        int status = pthread_rwlock_wrlock(&m_rwlock);
        POMAGMA_ASSERT1(status == 0, "pthread_rwlock_wrlock failed");
    }

    // glibc seems to be buggy; don't unlock more often than it has been locked
    // see http://sourceware.org/bugzilla/show_bug.cgi?id=4825
    void unlock ()
    {
        int status = pthread_rwlock_unlock(&m_rwlock);
        POMAGMA_ASSERT1(status == 0, "pthread_rwlock_unlock failed");
    }

    void lock_shared ()
    {
        int status = pthread_rwlock_rdlock(&m_rwlock);
        POMAGMA_ASSERT1(status == 0, "pthread_rwlock_rdlock failed");
    }

    void unlock_shared ()
    {
        unlock();
    }

    typedef unique_lock<SharedMutex> UniqueLock;
    typedef shared_lock<SharedMutex> SharedLock;
};



#if (POMAGMA_DEBUG_LEVEL == 0)

struct AssertSharedMutex
{
    struct UniqueLock { UniqueLock (AssertSharedMutex &) {} };
    struct SharedLock { SharedLock (AssertSharedMutex &) {} };
};

#else // (POMAGMA_DEBUG_LEVEL == 0)

class AssertSharedMutex
{
    std::atomic<size_t> m_shared;
    AssertMutex m_unique;

public:

    AssertSharedMutex () : m_shared(0), m_unique() {}

    void lock ()
    {
        m_unique.lock();
        POMAGMA_ASSERT(m_shared == 0, "lock while lock_shared");
    }

    void unlock ()
    {
        POMAGMA_ASSERT(m_shared == 0, "unllock while lock_shared");
        m_unique.unlock();
    }

    void lock_shared ()
    {
        ++m_shared;
        POMAGMA_ASSERT(not m_unique.is_locked(),
                "lock_shared while unique locked");
    }

    void unlock_shared ()
    {
        POMAGMA_ASSERT(not m_unique.is_locked(),
                "unlock_shared while unique locked");
        --m_shared;
    }

    typedef unique_lock<AssertSharedMutex> UniqueLock;
    typedef shared_lock<AssertSharedMutex> SharedLock;
};

#endif // (POMAGMA_DEBUG_LEVEL == 0)


} // namespace pomagma

#endif // POMAGMA_THREADING_HPP
