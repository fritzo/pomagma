#pragma once

// TODO try out google's tcmalloc:
// http://gperftools.googlecode.com/svn/trunk/doc/tcmalloc.html

#include <cstring>
#include <pomagma/util/util.hpp>

#if GCC_VERSION > 40700 || defined(__clang__)
#define assume_aligned(x)      \
    (static_cast<decltype(x)>( \
        __builtin_assume_aligned((x), BYTES_PER_CACHE_LINE)))
#else  // GCC_VERSION > 40700 || defined(__clang__)
#define assume_aligned(x) (x)
#endif  // GCC_VERSION > 40700 || defined(__clang__)

namespace pomagma {

template <class T>
inline bool is_aligned(const T *ptr, size_t alignment = BYTES_PER_CACHE_LINE) {
    return (reinterpret_cast<size_t>(ptr) & (alignment - 1)) == 0;
}

void *alloc_blocks(size_t block_size, size_t block_count,
                   size_t alignment = BYTES_PER_CACHE_LINE);

template <class T>
inline T *alloc_blocks(size_t block_count) {
    return static_cast<T *>(alloc_blocks(sizeof(T), block_count));
}

template <class T>
inline void zero_blocks(T *base, size_t count) {
    bzero(base, count * sizeof(T));
}

template <class T, class Init = T>
inline void construct_blocks(T *base, size_t count, Init init) {
    for (size_t i = 0; i < count; ++i) {
        new (base + i) T(init);
    }
}

template <class T>
inline void destroy_blocks(T *base, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        base[i].~T();
    }
}

void free_blocks(void *base);

// T must be default constructible.
template <class T>
class Padded : public T {
   public:
    Padded() {
        static_assert(is_power_of_two(sizeof(Padded<T>)),
                      "Padded object is not aligned");
    }

   private:
    char m_padding[static_power_of_two_padding<sizeof(T)>::val()];
};

}  // namespace pomagma
