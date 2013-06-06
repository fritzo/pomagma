#pragma once

// TODO try out google's tcmalloc:
// http://gperftools.googlecode.com/svn/trunk/doc/tcmalloc.html

#include <pomagma/platform/util.hpp>

#if __GNUC_PREREQ(4,7)
#  define assume_aligned(POMAGMA_arg) __builtin_assume_aligned(POMAGMA_arg, 32)
#else // __GNUC_PREREQ(4,7)
#  define assume_aligned(POMAGMA_arg) (POMAGMA_arg)
#endif // __GNUC_PREREQ(4,7)

extern "C" void bzero(void * data, size_t byte_count) throw ();

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
