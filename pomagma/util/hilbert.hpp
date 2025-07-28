#pragma once

#include <omp.h>  // For OpenMP parallelization

#include <algorithm>  // For std::clamp, std::min
#include <cstdint>    // For uint32_t, uint64_t, uint16_t
#include <tuple>      // For std::tuple, std::make_tuple

#ifdef __BMI2__
#include <immintrin.h>  // For BMI2 PEXT instructions
#endif

namespace pomagma {

/**
 * Ultra-fast O(1) Hilbert curve decode for 32-bit coordinates.
 * Supports 2^30 x 2^30 coordinate space using 60-bit Hilbert index.
 * (Full 2^32 x 2^32 would require 128-bit arithmetic)
 *
 * Uses "Hacker's Delight" parallel-prefix method optimized by Steele
 * for constant-time execution. On Intel Haswell+ CPUs with BMI2,
 * uses PEXT instruction for 50x speedup over naive implementations.
 */
inline std::tuple<uint32_t, uint32_t> hilbert_decode_30(uint64_t h) {
    constexpr uint32_t order = 30;  // 2^30 = 1,073,741,824 max coordinate

    uint64_t s = h;

    // Pad s on left with 01 pattern for parallel processing
    if (2 * order < 64) {
        s |= 0x5555555555555555ULL << (2 * order);
    }

    // Extract right-shifted bits for parallel operations
    const uint64_t sr = (s >> 1) & 0x5555555555555555ULL;

    // Compute complement & swap info using bit arithmetic trick
    uint64_t cs = ((s & 0x5555555555555555ULL) + sr) ^ 0x5555555555555555ULL;

    // Parallel prefix XOR to propagate complement/swap info left-to-right
    cs ^= (cs >> 2);
    cs ^= (cs >> 4);
    cs ^= (cs >> 8);
    cs ^= (cs >> 16);
    cs ^= (cs >> 32);

    // Extract swap and complement bits into separate masks
    const uint64_t swap = cs & 0x5555555555555555ULL;
    const uint64_t comp = (cs >> 1) & 0x5555555555555555ULL;

    // Apply transformations to compute final coordinates
    uint64_t t = (s & swap) ^ comp;
    s ^= sr ^ t ^ (t << 1);

    // Mask to remove padding bits
    s &= ((1ULL << (2 * order)) - 1);

#ifdef __BMI2__
    // Intel BMI2 PEXT optimization for 50x speedup on Haswell+ CPUs
    const uint32_t x =
        static_cast<uint32_t>(_pext_u64(s, 0xAAAAAAAAAAAAAAAAULL));
    const uint32_t y =
        static_cast<uint32_t>(_pext_u64(s, 0x5555555555555555ULL));
#else
    // Parallel bit deinterleaving using optimized bit manipulation
    // Note: ARM64 NEON doesn't have a direct equivalent to PEXT, so this
    // fallback works efficiently across all architectures (x86, ARM64, etc.)
    t = (s ^ (s >> 1)) & 0x2222222222222222ULL;
    s ^= t ^ (t << 1);
    t = (s ^ (s >> 2)) & 0x0C0C0C0C0C0C0C0CULL;
    s ^= t ^ (t << 2);
    t = (s ^ (s >> 4)) & 0x00F000F000F000F0ULL;
    s ^= t ^ (t << 4);
    t = (s ^ (s >> 8)) & 0x0000FF000000FF00ULL;
    s ^= t ^ (t << 8);
    t = (s ^ (s >> 16)) & 0x00000000FFFF0000ULL;
    s ^= t ^ (t << 16);

    const uint32_t x = static_cast<uint32_t>(s >> 32);
    const uint32_t y = static_cast<uint32_t>(s & 0xFFFFFFFFULL);
#endif

    return std::make_tuple(x, y);
}

/**
 * Ultra-fast O(1) Hilbert curve decode for 16-bit coordinates.
 * Supports 2^16 x 2^16 coordinate space using 32-bit Hilbert index.
 *
 * Optimized version for micro atlas operations with 16-bit E-class IDs.
 */
inline std::tuple<uint16_t, uint16_t> hilbert_decode_16(uint32_t h) {
    constexpr uint32_t order = 16;  // 2^16 = 65,536 max coordinate

    uint32_t s = h;

    // Pad s on left with 01 pattern for parallel processing
    if (2 * order < 32) {
        s |= 0x55555555U << (2 * order);
    }

    // Extract right-shifted bits for parallel operations
    const uint32_t sr = (s >> 1) & 0x55555555U;

    // Compute complement & swap info using bit arithmetic trick
    uint32_t cs = ((s & 0x55555555U) + sr) ^ 0x55555555U;

    // Parallel prefix XOR to propagate complement/swap info left-to-right
    cs ^= (cs >> 2);
    cs ^= (cs >> 4);
    cs ^= (cs >> 8);
    cs ^= (cs >> 16);

    // Extract swap and complement bits into separate masks
    const uint32_t swap = cs & 0x55555555U;
    const uint32_t comp = (cs >> 1) & 0x55555555U;

    // Apply transformations to compute final coordinates
    uint32_t t = (s & swap) ^ comp;
    s ^= sr ^ t ^ (t << 1);

    // Mask to remove padding bits
    if (2 * order < 32) {
        s &= ((1U << (2 * order)) - 1);
    } else {
        s &= 0xFFFFFFFFU;  // Keep all 32 bits
    }

#ifdef __BMI2__
    // Intel BMI2 PEXT optimization for 50x speedup on Haswell+ CPUs
    const uint16_t x = static_cast<uint16_t>(_pext_u32(s, 0xAAAAAAAAU));
    const uint16_t y = static_cast<uint16_t>(_pext_u32(s, 0x55555555U));
#else
    // Parallel bit deinterleaving using optimized bit manipulation
    // Note: ARM64 NEON doesn't have a direct equivalent to PEXT, so this
    // fallback works efficiently across all architectures (x86, ARM64, etc.)
    t = (s ^ (s >> 1)) & 0x22222222U;
    s ^= t ^ (t << 1);
    t = (s ^ (s >> 2)) & 0x0C0C0C0CU;
    s ^= t ^ (t << 2);
    t = (s ^ (s >> 4)) & 0x00F000F0U;
    s ^= t ^ (t << 4);
    t = (s ^ (s >> 8)) & 0x0000FF00U;
    s ^= t ^ (t << 8);

    const uint16_t x = static_cast<uint16_t>(s >> 16);
    const uint16_t y = static_cast<uint16_t>(s & 0xFFFFU);
#endif

    return std::make_tuple(x, y);
}

/**
 * Ultra-fast O(1) Hilbert curve decode for 8-bit coordinates.
 * Supports 2^8 x 2^8 coordinate space using 16-bit Hilbert index.
 *
 * Optimized version for very small coordinate spaces with 8-bit coordinates.
 */
inline std::tuple<uint8_t, uint8_t> hilbert_decode_8(uint16_t h) {
    constexpr uint32_t order = 8;  // 2^8 = 256 max coordinate

    uint16_t s = h;

    // Pad s on left with 01 pattern for parallel processing
    if (2 * order < 16) {
        s |= 0x5555U << (2 * order);
    }

    // Extract right-shifted bits for parallel operations
    const uint16_t sr = (s >> 1) & 0x5555U;

    // Compute complement & swap info using bit arithmetic trick
    uint16_t cs = ((s & 0x5555U) + sr) ^ 0x5555U;

    // Parallel prefix XOR to propagate complement/swap info left-to-right
    cs ^= (cs >> 2);
    cs ^= (cs >> 4);
    cs ^= (cs >> 8);

    // Extract swap and complement bits into separate masks
    const uint16_t swap = cs & 0x5555U;
    const uint16_t comp = (cs >> 1) & 0x5555U;

    // Apply transformations to compute final coordinates
    uint16_t t = (s & swap) ^ comp;
    s ^= sr ^ t ^ (t << 1);

    // Mask to remove padding bits
    if (2 * order < 16) {
        s &= ((1U << (2 * order)) - 1);
    } else {
        s &= 0xFFFFU;  // Keep all 16 bits
    }

#ifdef __BMI2__
    // Intel BMI2 PEXT optimization for 50x speedup on Haswell+ CPUs
    const uint8_t x = static_cast<uint8_t>(_pext_u32(s, 0xAAAAU));
    const uint8_t y = static_cast<uint8_t>(_pext_u32(s, 0x5555U));
#else
    // Parallel bit deinterleaving using optimized bit manipulation
    // Note: ARM64 NEON doesn't have a direct equivalent to PEXT, so this
    // fallback works efficiently across all architectures (x86, ARM64, etc.)
    t = (s ^ (s >> 1)) & 0x2222U;
    s ^= t ^ (t << 1);
    t = (s ^ (s >> 2)) & 0x0C0CU;
    s ^= t ^ (t << 2);
    t = (s ^ (s >> 4)) & 0x00F0U;
    s ^= t ^ (t << 4);

    const uint8_t x = static_cast<uint8_t>(s >> 8);
    const uint8_t y = static_cast<uint8_t>(s & 0xFFU);
#endif

    return std::make_tuple(x, y);
}

/**
 * Iterates over [1,size) x [1,size) in parallel Hilbert curve order.
 *
 * @param size Maximum coordinate value (exclusive)
 * @param func Function to call for each (x, y) coordinate pair
 * @param chunks_per_thread Number of chunks per thread
 * @param min_chunk_size Minimum chunk size
 * @param max_chunk_size Maximum chunk size
 */
template <typename Func>
inline void for_xy(size_t size, Func func, size_t chunks_per_thread = 16ULL,
                   size_t min_chunk_size = 64ULL,
                   size_t max_chunk_size = 4096ULL) {
    const size_t n = [size]() {
        size_t n = 1;
        while (n < size) n *= 2;  // Round to power of 2
        return n;
    }();
    const size_t num_threads = omp_get_max_threads();
    const size_t ideal_chunk_size = n * n / (num_threads * chunks_per_thread);
    const size_t chunk_size =
        std::clamp(ideal_chunk_size, min_chunk_size, max_chunk_size);

    if (n <= 65536U) {
        // Use 16-bit decoding for smaller coordinate spaces
        const uint32_t nn = n * n;
#pragma omp parallel for schedule(dynamic, chunk_size)
        for (uint32_t h = 0; h < nn; ++h) {
            auto [x, y] = hilbert_decode_16(h);
            if (x < size && y < size && x && y) {
                func(x, y);
            }
        }
    } else {
        // Use 30-bit decoding for larger coordinate spaces
        const uint64_t nn = n * n;
#pragma omp parallel for schedule(dynamic, chunk_size)
        for (uint64_t h = 0; h < nn; ++h) {
            auto [x, y] = hilbert_decode_30(h);
            if (x < size && y < size && x && y) {
                func(x, y);
            }
        }
    }
}

/**
 * Naive O(n) Hilbert curve encode for 16-bit coordinates.
 * Supports 2^16 x 2^16 coordinate space using 32-bit Hilbert index.
 *
 * Uses the Lam & Shapiro algorithm from Hacker's Delight.
 * This is the reference implementation - correct but not optimized.
 */
inline uint32_t hilbert_encode_16_naive(uint16_t x, uint16_t y) {
    // Implementation of Lam & Shapiro algorithm from Hacker's Delight
    // This converts 2D coordinates to Hilbert curve index

    constexpr int n = 16;  // number of bits per coordinate
    uint32_t s = 0;

    for (int i = n - 1; i >= 0; i--) {
        uint32_t xi = (x >> i) & 1U;
        uint32_t yi = (y >> i) & 1U;

        if (yi == 0) {
            uint32_t temp = x;
            x = y ^ (static_cast<uint16_t>(-static_cast<int32_t>(xi)));
            y = temp ^ (static_cast<uint16_t>(-static_cast<int32_t>(xi)));
        }

        s = 4 * s + 2 * xi + (xi ^ yi);
    }

    return s;
}

/**
 * Naive O(n) Hilbert curve encode for 8-bit coordinates.
 * Supports 2^8 x 2^8 coordinate space using 16-bit Hilbert index.
 *
 * Uses the Lam & Shapiro algorithm from Hacker's Delight.
 * This is the reference implementation - correct but not optimized.
 */
inline uint16_t hilbert_encode_8_naive(uint8_t x, uint8_t y) {
    // Implementation of Lam & Shapiro algorithm from Hacker's Delight
    // This converts 2D coordinates to Hilbert curve index

    constexpr int n = 8;  // number of bits per coordinate
    uint16_t s = 0;

    for (int i = n - 1; i >= 0; i--) {
        uint16_t xi = (x >> i) & 1U;
        uint16_t yi = (y >> i) & 1U;

        if (yi == 0) {
            uint16_t temp = x;
            x = y ^ (static_cast<uint8_t>(-static_cast<int16_t>(xi)));
            y = temp ^ (static_cast<uint8_t>(-static_cast<int16_t>(xi)));
        }

        s = 4 * s + 2 * xi + (xi ^ yi);
    }

    return s;
}

// Fast O(1) Hilbert curve encode for up to 16-bit coordinates.
// Adapted from @rawrunprotected's algorithm
// https://threadlocalmutex.com/?p=126
// https://github.com/rawrunprotected/hilbert_curves
inline uint32_t hilbert_encode_16(uint16_t x, uint16_t y) {
    uint32_t A, B, C, D;

    // Initial prefix scan round, prime with x and y
    {
        uint32_t a = x ^ y;
        uint32_t b = 0xFFFF ^ a;
        uint32_t c = 0xFFFF ^ (x | y);
        uint32_t d = x & (y ^ 0xFFFF);

        A = a | (b >> 1);
        B = (a >> 1) ^ a;

        C = ((c >> 1) ^ (b & (d >> 1))) ^ c;
        D = ((a & (c >> 1)) ^ (d >> 1)) ^ d;
    }

    {
        uint32_t a = A;
        uint32_t b = B;
        uint32_t c = C;
        uint32_t d = D;

        A = ((a & (a >> 2)) ^ (b & (b >> 2)));
        B = ((a & (b >> 2)) ^ (b & ((a ^ b) >> 2)));

        C ^= ((a & (c >> 2)) ^ (b & (d >> 2)));
        D ^= ((b & (c >> 2)) ^ ((a ^ b) & (d >> 2)));
    }

    {
        uint32_t a = A;
        uint32_t b = B;
        uint32_t c = C;
        uint32_t d = D;

        A = ((a & (a >> 4)) ^ (b & (b >> 4)));
        B = ((a & (b >> 4)) ^ (b & ((a ^ b) >> 4)));

        C ^= ((a & (c >> 4)) ^ (b & (d >> 4)));
        D ^= ((b & (c >> 4)) ^ ((a ^ b) & (d >> 4)));
    }

    // Final round and projection
    {
        uint32_t a = A;
        uint32_t b = B;
        uint32_t c = C;
        uint32_t d = D;

        C ^= ((a & (c >> 8)) ^ (b & (d >> 8)));
        D ^= ((b & (c >> 8)) ^ ((a ^ b) & (d >> 8)));
    }

    // Undo transformation prefix scan
    uint32_t a = C ^ (C >> 1);
    uint32_t b = D ^ (D >> 1);

    // Recover index bits
    uint32_t i0 = x ^ y;
    uint32_t i1 = b | (0xFFFF ^ (i0 | a));

    // Interleave function optimized for 16-bit result
    auto interleave = [](uint32_t x) -> uint32_t {
        x = (x | (x << 8)) & 0x00FF00FF;
        x = (x | (x << 4)) & 0x0F0F0F0F;
        x = (x | (x << 2)) & 0x33333333;
        x = (x | (x << 1)) & 0x55555555;
        return x;
    };

    return (interleave(i1) << 1) | interleave(i0);
}

inline uint16_t hilbert_encode_8(uint8_t x, uint8_t y) {
    return hilbert_encode_16(x, y);
}

}  // namespace pomagma