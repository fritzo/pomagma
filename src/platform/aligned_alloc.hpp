#pragma once

// TODO try out google's tcmalloc:
// http://gperftools.googlecode.com/svn/trunk/doc/tcmalloc.html

#include <pomagma/platform/util.hpp>
#include <cstring>

#if GCC_VERSION > 40700
#  define assume_aligned(x) \
    (static_cast<decltype(x)>(__builtin_assume_aligned(x, 32)))
#else // GCC_VERSION > 40700
#  define assume_aligned(x) (x)
#endif // GCC_VERSION > 40700

namespace pomagma
{

void * alloc_blocks (
        size_t block_size,
        size_t block_count,
        size_t alignment = 32);

template<class T>
inline T * alloc_blocks (size_t block_count)
{
  return static_cast<T *>(alloc_blocks(sizeof(T), block_count));
}

template<class T>
inline void zero_blocks (T * base, size_t count)
{
    bzero(base, count * sizeof(T));
}

template<class T, class Init = T>
inline void construct_blocks (T * base, size_t count, Init init)
{
    for (size_t i = 0; i < count; ++i) {
        new (base + i) T (init);
    }
}

template<class T>
inline void destroy_blocks (T * base, size_t count)
{
    for (size_t i = 0; i < count; ++i) {
        base[i].~T();
    }
}

void free_blocks (void * base);

} // namespace pomagma
