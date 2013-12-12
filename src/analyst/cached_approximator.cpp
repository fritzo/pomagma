#include <pomagma/analyst/cached_approximator.hpp>
#include <pomagma/platform/hash_map.hpp>

namespace pomagma
{

uint64_t HashedApproximation::compute_hash (const Approximation & approx)
{
    const size_t W = approx.upper.word_dim();
    const Word * restrict upper = approx.upper.raw_data();
    const Word * restrict lower = approx.lower.raw_data();

    FNV_hash::HashState state;
    state.add(approx.ob);
    for (size_t w = 0; w < W; ++w) {
        state.add(upper[w]);
    }
    for (size_t w = 0; w < W; ++w) {
        state.add(lower[w]);
    }
    return state.get();
}

} // namespace pomagma
