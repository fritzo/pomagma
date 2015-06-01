
#include <pomagma/util/aligned_alloc.hpp>

#define POMAGMA_DEBUG1(mess)
//#define POMAGMA_DEBUG1(mess) POMAGMA_DEBUG(message)

namespace pomagma
{

// allocates an aligned array, wraps posix_memalign
void * alloc_blocks (size_t block_size, size_t block_count, size_t alignment)
{
    POMAGMA_DEBUG1("Allocating " << block_count
                   << " blocks of size " << block_size << 'B');

    size_t byte_count = block_size * block_count;
    void * base;
    int info = posix_memalign(& base, alignment, byte_count);

    POMAGMA_ASSERT(info == 0,
            "posix_memalign failed to allocate " << byte_count << 'B');

    return base;
}

// just wraps free()
void free_blocks (void * base)
{
    POMAGMA_DEBUG1("Freeing blocks");

    free(base);
}

} // namespace pomagma
