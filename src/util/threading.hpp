#pragma once

#include <pomagma/util/util.hpp>
#include <mutex>
#include <atomic>
#include <pthread.h>

#ifdef POMAGMA_ASSUME_X86
#  define barrier() asm volatile("":::"memory")
#  define memory_barrier() asm volatile("mfence":::"memory")
#  define load_barrier() asm volatile("lfence":::"memory")
#  define store_barrier() asm volatile("sfence" ::: "memory")
#else // POMAGMA_ASSUME_X86
#  warn "defaulting to full memory barriers"
#  define barrier() __sync_synchronize()
#  define memory_barrier() __sync_synchronize()
#  define load_barrier() __sync_synchronize()
#  define store_barrier() __sync_synchronize()
#endif // POMAGMA_ASSUME_X86

// these do not prevent compiler from reordering non-atomic loads/stores
//#define memory_barrier() std::atomic_thread_fence(std::memory_order_acq_rel)
//#define acquire_barrier() std::atomic_thread_fence(std::memory_order_acquire)
//#define release_barrier() std::atomic_thread_fence(std::memory_order_release)

namespace pomagma
{

// add default constructor for use in std::vector
struct atomic_flag : std::atomic_flag
{
    atomic_flag () : std::atomic_flag(ATOMIC_FLAG_INIT)
    {
        test_and_set();
    }
    atomic_flag (const atomic_flag &)
        : std::atomic_flag(ATOMIC_FLAG_INIT)
    {
        POMAGMA_ERROR("fail");
    }
    void operator= (const atomic_flag &) { POMAGMA_ERROR("fail"); }
};

typedef std::memory_order order_t;
const order_t relaxed = std::memory_order_relaxed;
const order_t acquire = std::memory_order_acquire;
const order_t release = std::memory_order_release;

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
    void lock () { load_barrier(); }
    void unlock () { store_barrier(); }
    struct Lock
    {
        Lock (AssertMutex &) { load_barrier(); }
        ~Lock () { store_barrier(); }
    };
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
        load_barrier();
        bool expected = false;
        POMAGMA_ASSERT(m_flag.compare_exchange_strong(expected, true),
                "lock contention");
    }

    void unlock ()
    {
        bool expected = true;
        POMAGMA_ASSERT(m_flag.compare_exchange_strong(expected, false),
                "unlock contention");
        store_barrier();
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
        int status = pthread_rwlock_init(&m_rwlock, nullptr);
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
    struct UniqueLock
    {
        UniqueLock (AssertSharedMutex &) { load_barrier(); }
        ~UniqueLock () { store_barrier(); }
    };
    struct SharedLock
    {
        SharedLock (AssertSharedMutex &) { load_barrier(); }
        ~SharedLock () { store_barrier(); }
    };
};

#else // (POMAGMA_DEBUG_LEVEL == 0)

class AssertSharedMutex
{
    std::atomic<int_fast64_t> m_count; // unique < 0, shared > 0

public:

    AssertSharedMutex () : m_count(0) {}

    void lock ()
    {
        load_barrier();
        POMAGMA_ASSERT(--m_count < 0, "lock contention");
    }

    void unlock ()
    {
        ++m_count;
        store_barrier();
    }

    void lock_shared ()
    {
        load_barrier();
        POMAGMA_ASSERT(++m_count > 0, "lock_shared contention");
    }

    void unlock_shared ()
    {
        --m_count;
        store_barrier();
    }

    typedef unique_lock<AssertSharedMutex> UniqueLock;
    typedef shared_lock<AssertSharedMutex> SharedLock;
};

#endif // (POMAGMA_DEBUG_LEVEL == 0)


} // namespace pomagma
