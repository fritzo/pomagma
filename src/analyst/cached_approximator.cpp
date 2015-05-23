#include <pomagma/analyst/cached_approximator.hpp>
#include <pomagma/platform/hash_map.hpp>

namespace pomagma
{

// TODO profile hash conflict rate
uint64_t HashedSet::compute_hash (const DenseSet & set)
{
    const size_t W = set.word_dim();
    const Word * restrict data = set.raw_data();

    FNV_hash::HashState state;
    for (size_t w = 0; w < W; ++w) {
        state.add(data[w]);
    }
    return state.get();
}

// TODO profile hash conflict rate
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
