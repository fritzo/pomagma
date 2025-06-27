# Design Doc: Custom Kernels for E-graph Inference

## Objective

Accelerate forward-chaining E-graph inference through custom kernel optimizations, including GPU acceleration and advanced cache-friendly algorithms.

## Background

### Pomagma's Inference Bottlenecks

Profiling data from `doc/benchmarks.md` reveals specific hotspots consuming most execution time:

- **Line 4837**: 59% of time, 17.9M calls - Complex NLESS transitivity operations
- **Line 906**: 10.25% of time, 528 calls - Composition rules for COMP/APP functions  
- **Line 914**: 7.77% of time, 528 calls - More composition rules
- **Line 1146**: 6.81% of time, 282 calls - Transpose operations

The dominant bottleneck is NLESS (not-less-than) inference consuming nearly 60% of runtime. This involves checking transitivity patterns across millions of E-class pairs using set intersection operations.

**Batch inference algorithms** in `pomagma/cartographer/infer.cpp` implement mathematical properties like transitivity (`LESS x z, LESS z y ==> LESS x y`) and monotonicity (`LESS f g, LESS x y ==> LESS fun(f,x) fun(g,y)`). These feature embarrassingly parallel outer loops over E-classes with nested set operations and hash table lookups.

**Atlas size differences**: Pomagma uses different identifier widths for different scales:
- **Micro atlas** (`pomagma/atlas/micro/`): 16-bit E-class IDs (`typedef uint16_t Ob`) supporting up to 65,535 E-classes, used by surveyor for concurrent E-graph growth
- **Macro atlas** (`pomagma/atlas/macro/`): 32-bit E-class IDs (`typedef uint32_t Ob`) supporting up to 4 billion E-classes, used by cartographer and analyst for large-scale batch processing

**Memory access patterns** are read-heavy (~1000:1 read/write ratio) with sequential bitwise operations on `DenseSet` structures and random hash table probes for function lookups. The `DenseSet` operations use vectorized code (`POMAGMA_VECTORIZE_LOOP`) for set intersection, union, and difference computations.

### Cache-Friendly Algorithms

**Hilbert curves** are space-filling curves that map 2D coordinates to 1D while preserving locality. They achieve superior cache performance compared to row-major traversal by keeping spatially close data points temporally close in memory access patterns.

For matrix-like operations (similar to NLESS transitivity checking), Hilbert curves can reduce cache misses by 50-70% compared to naive nested loops. Research shows 30-40% speedups are common for large sparse matrices using Hilbert traversal patterns.

**Loop tiling (blocking)** divides iteration spaces into smaller blocks fitting in cache. Intel's compiler directives like `#pragma block_loop` can automatically tile loops when optimization level O3 is used. Manual blocking often achieves 2-6x speedups for memory-bound operations.

**Cache-oblivious algorithms** work efficiently across all cache levels without explicit cache size knowledge. They use recursive divide-and-conquer patterns that naturally adapt to memory hierarchy, ideal for algorithms with unknown data sizes.

**Note on SIMD intrinsics**: For simple bitwise operations on arrays (like `DenseSet` intersections), modern compilers excel at auto-vectorization. Explicit SIMD intrinsics add platform-specific complexity without significant benefit for these straightforward operations. Pomagma's existing `POMAGMA_VECTORIZE_LOOP` directives already enable effective compiler auto-vectorization across Intel, AMD, and ARM architectures.

### CPU vs GPU Characteristics

**CPUs** excel through 64-byte cache lines matching Pomagma's tiled data, hardware prefetching for sequential access, 99%+ branch prediction accuracy, and AVX-512 SIMD for vectorized set operations. Current implementations use OpenMP across 16-32 cores.

**NVIDIA GPUs** provide 1000+ GB/s memory bandwidth vs ~120 GB/s for CPU, plus massive parallelism through thousands of cores. However, they suffer from 200-600 cycle memory latency, branch divergence penalties within 32-thread warps, and limited cache hierarchy.

**Apple Silicon** offers unique advantages through unified memory architecture eliminating CPU-GPU data transfer costs. The M2 Ultra provides ~800 GB/s memory bandwidth with 76-core GPU sharing 128GB unified memory with 20-core CPU.

## Feasibility of GPU Migration

GPU acceleration faces fundamental challenges but shows promise for specific algorithms.

**Cost analysis**: GPU instances cost 2-10x more than CPU equivalents. AWS p3.2xlarge (V100) costs $3.06/hour vs c5.9xlarge (36 vCPU) at $1.53/hour. 

**Incremental inference** (VM execution) appears unsuitable due to complex control flow, frequent branching, and atomic operations causing warp divergence and serialization.

**Batch inference** shows promise. Algorithms like `infer_less_transitive` have perfectly parallel outer loops. However, sparse memory access patterns and load imbalancing may limit speedups to 3-5x, below the 10x threshold needed for cost-effectiveness.

**Apple Silicon advantage**: Unified memory eliminates data transfer costs and enables tighter CPU-GPU cooperation, potentially improving the cost-benefit calculation.

## Design Details

### Profiling

Pomagma includes comprehensive profiling infrastructure:

- **VM Profiler** (`pomagma/util/profiler.hpp`) - Times individual VM program execution with microsecond precision
- **Dense Set Profiling** (`pomagma/util/sequential/dense_set_profile.cpp`) - Benchmarks vectorized set operations  
- **Threading Profiling** (`pomagma/util/threading_profile.cpp`) - Measures parallel execution overhead
- **Component Profilers** - Available via `make profile-misc`, `make profile-cartographer`, `make profile-surveyor`

Profiling reveals that DenseSet operations (intersection, union) achieve 100-1000 kHz on 64KB sets, while VM programs process millions of calls per second but with complex branching patterns unsuitable for GPU execution.

### Custom Kernel Designs

#### 1. Hilbert-Curve Transitivity Kernel (CPU)

**Target**: NLESS transitivity (59% of runtime) using cache-oblivious traversal patterns.

**Mathematical pattern**: Check transitivity `∃z: LESS(x,z) ∧ LESS(z,y)` using space-filling curve traversal.

**Current implementation**:
```cpp
for (Ob x = 1; x <= item_dim; ++x) {
    for (Ob y = 1; y <= item_dim; ++y) {
        if (check_transitivity(x, y)) process_pair(x, y);
    }
}
```

**Hilbert-curve optimization**:
```cpp
#include <omp.h>        // For OpenMP parallelization
#ifdef __BMI2__
#include <immintrin.h>  // For BMI2 PEXT instructions
#endif

// 32-bit Hilbert decode for macro atlas (cartographer, analyst)  
// Supports 2^30 x 2^30 coordinate space using 60-bit Hilbert index
// (Full 2^32 x 2^32 would require 128-bit arithmetic)
inline std::tuple<uint32_t, uint32_t> hilbert_decode_30(uint64_t h) {
    constexpr uint32_t order = 30;  // 2^30 = 1,073,741,824 max coordinate
    
    uint64_t s = h;
    
    // Pad s on left with 01 pattern for parallel processing
    s |= 0x5555555555555555ULL << (2 * order);
    
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
    const uint32_t x = static_cast<uint32_t>(_pext_u64(s, 0xAAAAAAAAAAAAAAAAULL));
    const uint32_t y = static_cast<uint32_t>(_pext_u64(s, 0x5555555555555555ULL));
#else
    // Parallel bit deinterleaving using optimized bit manipulation
    // Note: ARM64 NEON doesn't have a direct equivalent to PEXT, so this fallback
    // works efficiently across all architectures (x86, ARM64, etc.)
    t = (s ^ (s >> 1)) & 0x2222222222222222ULL; s ^= t ^ (t << 1);
    t = (s ^ (s >> 2)) & 0x0C0C0C0C0C0C0C0CULL; s ^= t ^ (t << 2);
    t = (s ^ (s >> 4)) & 0x00F000F000F000F0ULL; s ^= t ^ (t << 4);
    t = (s ^ (s >> 8)) & 0x0000FF000000FF00ULL; s ^= t ^ (t << 8);
    t = (s ^ (s >> 16)) & 0x00000000FFFF0000ULL; s ^= t ^ (t << 16);
    
    const uint32_t x = static_cast<uint32_t>(s >> 32);
    const uint32_t y = static_cast<uint32_t>(s & 0xFFFFFFFFULL);
#endif
    
    return std::make_tuple(x, y);
}

// 16-bit Hilbert decode for micro atlas (surveyor)
// Supports 2^16 x 2^16 coordinate space using 32-bit Hilbert index
inline std::tuple<uint16_t, uint16_t> hilbert_decode_16(uint32_t h) {
    constexpr uint32_t order = 16;  // 2^16 = 65,536 max coordinate
    
    uint32_t s = h;
    
    // Pad s on left with 01 pattern for parallel processing
    s |= 0x55555555U << (2 * order);
    
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
    s &= ((1U << (2 * order)) - 1);
    
#ifdef __BMI2__
    // Intel BMI2 PEXT optimization for 50x speedup on Haswell+ CPUs
    const uint16_t x = static_cast<uint16_t>(_pext_u32(s, 0xAAAAAAAAU));
    const uint16_t y = static_cast<uint16_t>(_pext_u32(s, 0x55555555U));
#else
    // Parallel bit deinterleaving using optimized bit manipulation
    // Note: ARM64 NEON doesn't have a direct equivalent to PEXT, so this fallback
    // works efficiently across all architectures (x86, ARM64, etc.)
    t = (s ^ (s >> 1)) & 0x22222222U; s ^= t ^ (t << 1);
    t = (s ^ (s >> 2)) & 0x0C0C0C0CU; s ^= t ^ (t << 2);
    t = (s ^ (s >> 4)) & 0x00F000F0U; s ^= t ^ (t << 4);
    t = (s ^ (s >> 8)) & 0x0000FF00U; s ^= t ^ (t << 8);
    
    const uint16_t x = static_cast<uint16_t>(s >> 16);
    const uint16_t y = static_cast<uint16_t>(s & 0xFFFFU);
#endif
    
    return std::make_tuple(x, y);
}

void hilbert_transitivity_macro(uint32_t size) {
    uint32_t n = 1;
    while (n < size) n *= 2;  // Round to power of 2
    
    const uint64_t total_points = static_cast<uint64_t>(n) * n;
    
    // Adaptive chunk sizing for cache efficiency vs load balancing
    // Larger chunks preserve Hilbert locality, but smaller chunks improve load balancing
    // when many coordinates fall outside the actual size
    const int num_threads = omp_get_max_threads();
    const uint64_t base_chunk = total_points / (num_threads * 4);  // 4 chunks per thread
    const uint64_t chunk_size = std::clamp(base_chunk, 1000ULL, 50000ULL);
    
    #pragma omp parallel for schedule(dynamic, chunk_size)
    for (uint64_t h = 0; h < total_points; ++h) {
        auto [x, y] = hilbert_decode_30(h);
        if (x < size && y < size) {
            if (check_transitivity(x, y)) process_pair(x, y);
        }
    }
}

void hilbert_transitivity_micro(uint16_t size) {
    uint16_t n = 1;
    while (n < size) n *= 2;  // Round to power of 2
    
    const uint32_t total_points = static_cast<uint32_t>(n) * n;
    
    // Smaller chunks for micro atlas due to smaller coordinate space
    const int num_threads = omp_get_max_threads();
    const uint32_t base_chunk = total_points / (num_threads * 4);
    const uint32_t chunk_size = std::clamp(base_chunk, 256U, 8192U);
    
    #pragma omp parallel for schedule(dynamic, chunk_size)
    for (uint32_t h = 0; h < total_points; ++h) {
        auto [x, y] = hilbert_decode_16(h);
        if (x < size && y < size) {
            if (check_transitivity(x, y)) process_pair(x, y);
        }
    }
}
```

**Parallelization strategy**:
- **Dynamic scheduling**: Handles load imbalancing when many coordinates fall outside actual E-graph size
- **Adaptive chunking**: Balances cache locality (larger chunks preserve Hilbert ordering) vs load balancing (smaller chunks distribute work more evenly)
- **Chunk size bounds**: 1K-50K for macro, 256-8K for micro atlas to maintain reasonable cache efficiency
- **Thread scaling**: Automatically adapts to available CPU cores while preserving spatial locality benefits

**Performance characteristics**:
- **O(1) decode complexity**: No loops in Hilbert decode, only bit manipulation operations
- **BMI2 optimization**: 50x faster than naive implementations on Intel Haswell+ CPUs (when available)
- **ARM64 compatibility**: Fallback bit manipulation works efficiently on Apple Silicon and other ARM64 processors
- **Dual precision**: 16-bit version for surveyor (micro atlas), 30-bit version for cartographer (macro atlas)
- **Practical range**: 30-bit coordinates support 1 billion × 1 billion grids, far exceeding typical E-graph sizes
- **OpenMP parallelization**: Linear scaling across CPU cores with preserved cache locality
- **Cache efficiency**: 30-40% speedup for large E-graphs through improved spatial locality
- **Expected speedup**: 30-40% cache improvement × 8-32 CPU cores = 4-20x total acceleration

#### 2. Blocked Matrix Transitivity Kernel (CPU)

**Target**: NLESS operations with explicit loop tiling for L1/L2/L3 cache optimization.

**Loop tiling implementation**:
```cpp
void blocked_transitivity(const DenseSet* LESS_matrix, uint32_t size) {
    constexpr uint32_t L1_BLOCK = 64;    // Fit in L1 cache
    constexpr uint32_t L2_BLOCK = 512;   // Fit in L2 cache
    
    #pragma omp parallel for collapse(2)
    for (uint32_t xi = 0; xi < size; xi += L2_BLOCK) {
        for (uint32_t yi = 0; yi < size; yi += L2_BLOCK) {
            for (uint32_t zi = 0; zi < size; zi += L2_BLOCK) {
                for (uint32_t x = xi; x < std::min(xi + L2_BLOCK, size); x += L1_BLOCK) {
                    for (uint32_t y = yi; y < std::min(yi + L2_BLOCK, size); y += L1_BLOCK) {
                        for (uint32_t z = zi; z < std::min(zi + L2_BLOCK, size); z += L1_BLOCK) {
                            blocked_inner_kernel(LESS_matrix, x, y, z, L1_BLOCK, size);
                        }
                    }
                }
            }
        }
    }
}

void blocked_inner_kernel(const DenseSet* LESS, uint32_t x0, uint32_t y0, uint32_t z0, 
                         uint32_t block_size, uint32_t size) {
    for (uint32_t x = x0; x < std::min(x0 + block_size, size); ++x) {
        for (uint32_t y = y0; y < std::min(y0 + block_size, size); ++y) {
            for (uint32_t z = z0; z < std::min(z0 + block_size, size); ++z) {
                if (LESS[x].contains(z) && LESS[z].contains(y)) {
                    infer_less(x, y);
                }
            }
        }
    }
}
```

Expected speedup: 2-4x through reduced cache misses.

#### 3. GPU Sparse Matrix Transitivity Kernel (GPU)

**Target**: Transitivity checking for sparse LESS relations using GPU.

**CUDA implementation**:
```cuda
__global__ void gpu_sparse_transitivity(
    const uint32_t* row_ptr, const uint32_t* col_idx, 
    uint32_t* results, uint32_t num_rows) {
    
    uint32_t x = blockIdx.x * blockDim.x + threadIdx.x;
    if (x >= num_rows) return;
    
    __shared__ uint32_t shared_cols[1024];
    
    // Load x's neighbors into shared memory
    uint32_t x_start = row_ptr[x];
    uint32_t x_end = row_ptr[x + 1];
    uint32_t x_degree = x_end - x_start;
    
    for (uint32_t i = threadIdx.x; i < x_degree; i += blockDim.x) {
        if (i < 1024) shared_cols[i] = col_idx[x_start + i];
    }
    __syncthreads();
    
    // Check transitivity for each y
    for (uint32_t y = 0; y < num_rows; ++y) {
        bool found = false;
        uint32_t y_start = row_ptr[y];
        uint32_t y_end = row_ptr[y + 1];
        
        // Binary search intersection in shared memory
        for (uint32_t j = y_start; j < y_end && !found; ++j) {
            uint32_t z = col_idx[j];
            
            // Binary search for z in shared_cols
            int left = 0, right = min(x_degree, 1024) - 1;
            while (left <= right) {
                int mid = (left + right) / 2;
                if (shared_cols[mid] == z) { found = true; break; }
                if (shared_cols[mid] < z) left = mid + 1;
                else right = mid - 1;
            }
        }
        
        if (found) atomicAdd(&results[x * num_rows + y], 1);
    }
}
```

Expected speedup: 3-5x for sparse graphs on modern GPUs.

#### 4. Cache-Oblivious Composition Kernel (CPU)

**Target**: COMP/APP composition rules (Lines 906/914, ~18% runtime) using recursive divide-and-conquer.

**Cache-oblivious implementation**:
```cpp
void cache_oblivious_composition(uint32_t start_x, uint32_t end_x, 
                                uint32_t start_y, uint32_t end_y,
                                uint32_t start_z, uint32_t end_z) {
    const uint32_t THRESHOLD = 64;
    
    if ((end_x - start_x) * (end_y - start_y) * (end_z - start_z) < THRESHOLD) {
        // Base case: direct computation
        for (uint32_t x = start_x; x < end_x; ++x) {
            for (uint32_t y = start_y; y < end_y; ++y) {
                for (uint32_t z = start_z; z < end_z; ++z) {
                    if (COMP.find(x, y) && APP.find(y, z)) {
                        infer_comp_app(x, z);
                    }
                }
            }
        }
    } else {
        // Recursive subdivision
        uint32_t mid_x = (start_x + end_x) / 2;
        uint32_t mid_y = (start_y + end_y) / 2;
        uint32_t mid_z = (start_z + end_z) / 2;
        
        // 8 recursive calls for 3D subdivision
        cache_oblivious_composition(start_x, mid_x, start_y, mid_y, start_z, mid_z);
        cache_oblivious_composition(start_x, mid_x, start_y, mid_y, mid_z, end_z);
        cache_oblivious_composition(start_x, mid_x, mid_y, end_y, start_z, mid_z);
        cache_oblivious_composition(start_x, mid_x, mid_y, end_y, mid_z, end_z);
        cache_oblivious_composition(mid_x, end_x, start_y, mid_y, start_z, mid_z);
        cache_oblivious_composition(mid_x, end_x, start_y, mid_y, mid_z, end_z);
        cache_oblivious_composition(mid_x, end_x, mid_y, end_y, start_z, mid_z);
        cache_oblivious_composition(mid_x, end_x, mid_y, end_y, mid_z, end_z);
    }
}
```

Expected speedup: 2-3x through automatic cache adaptation across all levels.

## References

### Space-Filling Curves and Cache-Oblivious Algorithms

- Yzelman, A. N., & Bisseling, R. H. (2010). "A cache-oblivious sparse matrix-vector multiplication scheme based on the Hilbert curve." *arXiv preprint*. [PDF](http://www.staff.science.uu.nl/~bisse101/Articles/yzelman10a_pre.pdf)

- Böhm, C., Perdacher, M., & Plant, C. (2018). "A novel hilbert curve for cache-locality preserving loops." *IEEE Transactions on Big Data*. [arXiv](https://arxiv.org/pdf/1606.06133v1.pdf)

- Frigo, M., Leiserson, C. E., Prokop, H., & Ramachandran, S. (1999). "Cache-oblivious algorithms." *Proceedings of the 40th Annual Symposium on Foundations of Computer Science*, 285-298.

### Ultra-Fast Hilbert Curve Algorithms

- Wunkolo: [qHilbert - Vectorized speedup of Hilbert curve generation using SIMD intrinsics](https://github.com/Wunkolo/qHilbert) - Achieves 50x speedup using BMI2 PEXT instructions

- Warren, H. S. (2012). "Hacker's Delight, 2nd Edition" - Chapter on Hilbert curves with parallel-prefix constant-time algorithms

- Lam, W. M., & Shapiro, J. M. (1994). "A class of fast algorithms for the Peano-Hilbert space-filling curve." *IBM Journal of Research and Development*, 38(5), 525-536.

- Butz, A. R. (1969). "Convergence with Hilbert's space filling curve." *Journal of Computer and System Sciences*, 3(2), 128-146.

### Loop Tiling and Cache Optimization

- Wikipedia: [Loop nest optimization](https://en.wikipedia.org/wiki/Loop_nest_optimization)

- Intel Developer Guide: [Cache Blocking Techniques](https://www.intel.com/content/www/us/en/developer/articles/technical/cache-blocking-techniques.html)

- Intel Developer Guide: [Loop Optimizations Where Blocks are Required](https://www.intel.com/content/www/us/en/developer/articles/technical/loop-optimizations-where-blocks-are-required.html)

### Auto-Vectorization and Compiler Optimization

- GCC Manual: [Auto-vectorization in GCC](https://gcc.gnu.org/projects/tree-ssa/vectorization.html)

- Clang/LLVM: [Loop Vectorization](https://llvm.org/docs/Vectorizers.html)

- Agner Fog's Optimization Manuals: [Software optimization resources](https://www.agner.org/optimize/)

### GPU Computing and Sparse Matrix Algorithms

- NVIDIA CUDA Programming Guide: [CUDA Toolkit Documentation](https://docs.nvidia.com/cuda/)

- Bell, N., & Garland, M. (2009). "Implementing sparse matrix-vector multiplication on throughput-oriented processors." *Proceedings of the Conference on High Performance Computing Networking, Storage and Analysis*, 1-11.

### Performance Analysis and Profiling

- Intel VTune Profiler: [Performance Analysis Tool](https://www.intel.com/content/www/us/en/developer/tools/oneapi/vtune-profiler.html)

- PAPI: [Performance Application Programming Interface](https://icl.utk.edu/papi/)

- Valgrind: [Memory Debugging and Profiling](https://valgrind.org/) 