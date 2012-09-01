#ifndef POMAGMA_THREADING_HPP
#define POMAGMA_THREADING_HPP

#include "util.hpp"
#include <pthread.h>
#include <mutex>
#include <boost/thread/locks.hpp>

namespace pomagma
{

struct Mutex : std::mutex
{
    typedef std::lock_guard<Mutex> Lock;
};

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

    bool try_lock ()
    {
        int status = pthread_rwlock_trywrlock(&m_rwlock);

        switch (status)
        {
            case 0:
                return true;

            case EBUSY:
                return false;

            case EDEADLK:
            default:
                POMAGMA_ERROR("deadlock");
        }
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

    bool try_lock_shared ()
    {
        int status = pthread_rwlock_tryrdlock(&m_rwlock);

        if (status == 0)
            return true;
        if (status == EBUSY)
            return false;

        POMAGMA_ERROR("pthread_rwlock_trylock failed");
    }

    void unlock_shared ()
    {
        unlock();
    }

    typedef boost::unique_lock<SharedMutex> SharedLock;
    typedef boost::shared_lock<SharedMutex> UniqueLock;
};

} // namespace pomagma

#endif // POMAGMA_THREADING_HPP
