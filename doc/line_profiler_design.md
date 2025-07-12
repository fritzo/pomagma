# Design Doc: Line Profiling Query Plan Programs

## Objective

Provide finer grained profiling information about theory/*.optimized.programs to aid decision making in performance optimization.

## Background

### Pomagma's existing profiling machinery

Pomagma tracks VM program performance using `ProgramProfiler` in `pomagma/util/profiler.hpp`. The system times entire program executions with RAII blocks and reports aggregate statistics by line number in `.optimized.programs` files. Each call to `VirtualMachine::execute()` gets wrapped with a timing block:

```cpp
// In vm.hpp
void execute(Program program) const {
    Context *context = new_context();
    ProgramProfiler::Block profiler(context->profiler, program);
    _execute(program, context);
}

// In profiler.hpp  
class Block : noncopyable {
    Block(ProgramProfiler &profiler, const void *program);
    ~Block() {
        m_stat.count += 1;
        m_stat.time += m_timer.elapsed_us();
    }
};
```

The profiler collects statistics across all threads and maps program pointers to line numbers using the `Agenda` class. Results appear in logs as aggregate program-level statistics.

Current profiling shows line-level granularity but not instruction-level detail within programs. Large programs contain hundreds of VM instructions, making it hard to find specific performance bottlenecks. The existing `POMAGMA_TRACE_VM` flag could provide instruction visibility but adds too much logging overhead for production use.

#### Example

At version 0.3.1, pomagma's surveyor produced the following profiling results
```
Profile of VirtualMachine programs:
 Line       Calls Percent   Total sec Per call sec
----- ----------- ------- ----------- ------------
 6439    12416522   94.03   718639.63      0.06
 1116        2020    1.34    10243.00      5.07
 1356        2020    1.10     8438.44      4.18
 1124        2020    0.93     7121.56      3.53
 1070        2222    0.45     3424.74      1.54
...
```
which is dominated by the NLESS program in `pomagma/theory/skja.optimized.programs`:
```
# plan 65: 4952 bytes
GIVEN_BINARY_RELATION NLESS a b
SEQUENCE 16
LETS_BINARY_RELATION_RHS LESS c b
LETS_BINARY_RELATION_LHS NLESS a d
FOR_POS_NEG e c d
INFER_BINARY_RELATION NLESS a e
SEQUENCE 16
LETS_BINARY_RELATION_LHS LESS a c
LETS_BINARY_RELATION_RHS NLESS d b
FOR_POS_NEG e c d
INFER_BINARY_RELATION NLESS e b
SEQUENCE 35
IF_NULLARY_FUNCTION Y b
FOR_NULLARY_FUNCTION I c
FOR_NULLARY_FUNCTION S d
FOR_BINARY_FUNCTION_LHS_RHS APP d c e
FOR_BINARY_FUNCTION_LHS_RHS APP e a f
SEQUENCE 8
IF_BINARY_RELATION LESS a f
INFER_BINARY_RELATION NLESS f a
IF_BINARY_RELATION LESS f a
INFER_BINARY_RELATION NLESS a f
...
```

This 4952-byte program contains dozens of VM instructions but current profiling only shows total execution time. Engineers cannot tell whether the bottleneck lies in the `FOR_POS_NEG` loops, the relation lookups, or the inference operations. Line-level profiling would identify which specific instructions consume the most time within this dominant program.

### Portable machinery for low-overhead profiling

Statistical sampling profilers achieve <1% overhead by sampling execution state periodically instead of instrumenting every operation. Sampling 0.01% of executions provides enough statistical accuracy for optimization while adding minimal performance cost. 

**Timing mechanisms** vary by platform but all provide sub-microsecond resolution:
- x86/x86_64: `rdtsc` instruction reads cycle counter (~20 cycles)
- ARM64: `cntvct_el0` register reads virtual timer (~15 cycles)  
- Apple Silicon: `mach_absolute_time()` system call (~10 cycles)
- Cross-platform: `std::chrono::steady_clock` (50-200 cycles, varies by OS)

**Random number generation** enables unbiased sampling decisions. Simple generators work well for profiling:
- Linear Congruential Generator: ~5 cycles, adequate quality
- Xorshift: ~10 cycles, better statistical properties
- PCG: ~15 cycles, excellent quality but slower

Thread-local generators avoid synchronization overhead that would dominate profiling cost in multi-threaded workloads like Pomagma's parallel VM execution.

**Lock-free data structures** enable concurrent sample collection without blocking VM threads. Atomic operations with relaxed memory ordering provide adequate consistency for statistical data while avoiding expensive synchronization.

## Design overview

The line profiler adds instruction-level sampling to Pomagma's existing program-level profiling. The system samples VM instructions at random points in time (roughly every 100μs) using fast timers and stochastic rounding with integer arithmetic, recording byte offsets in a single lock-free histogram that matches the `ProgramParser::m_program_data` layout. The sampling naturally weights by execution time rather than instruction count, ensuring slow instructions get sampled more frequently than fast ones. A post-processing script merges the histogram with `.optimized.programs` files to show execution time per instruction, helping engineers find bottlenecks within complex programs like the 4952-byte NLESS rule.

## Design details

### Low-overhead clock

Fast timing requires platform-specific code but with a common interface. The implementation abstracts platform differences while using the fastest available timer on each architecture.

```cpp
class FastClock {
    static constexpr uint64_t UPDATE_INTERVAL = 1000000; // cycles
    thread_local static uint64_t base_time_ns;
    thread_local static uint64_t base_counter;
    
public:
    static uint64_t now() {
        uint64_t counter = read_counter();
        if (unlikely(counter - base_counter > UPDATE_INTERVAL)) {
            calibrate();
        }
        return base_time_ns + counter_to_ns(counter - base_counter);
    }
    
private:
    static inline uint64_t read_counter() {
#if defined(__x86_64__) || defined(__i386__)
        uint32_t hi, lo;
        __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
        return ((uint64_t)hi << 32) | lo;
#elif defined(__aarch64__)
        uint64_t counter;
        __asm__ volatile("mrs %0, cntvct_el0" : "=r"(counter));
        return counter;
#elif defined(__APPLE__)
        return mach_absolute_time();
#else
        // Fallback to standard library
        return std::chrono::steady_clock::now().time_since_epoch().count();
#endif
    }
    
    static void calibrate() {
        auto real_time = std::chrono::steady_clock::now();
        base_time_ns = real_time.time_since_epoch().count();
        base_counter = read_counter();
    }
};
```

The calibration mechanism runs every ~1M cycles to track frequency scaling and maintain accuracy. Each platform uses its fastest timer: x86 uses `rdtsc` cycle counter, ARM64 uses virtual timer register, Apple uses the optimized system timer, and other platforms fall back to standard library clocks.

### Low-cost random number generation

Fast sampling decisions need cheap random numbers. Thread-local Xorshift generators provide good quality at ~10 cycles per call while avoiding synchronization between VM execution threads.

```cpp
class FastRNG {
    thread_local static uint64_t state;
    
public:
    static void init() {
        // Initialize with thread ID and timestamp to avoid identical sequences
        state = std::hash<std::thread::id>{}(std::this_thread::get_id()) ^
                std::chrono::steady_clock::now().time_since_epoch().count();
        if (state == 0) state = 1; // Avoid zero state
    }
    
    static uint32_t next() {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        return static_cast<uint32_t>(state);
    }
    
    static bool should_sample(uint32_t rate_per_million) {
        return next() % 1000000 < rate_per_million;
    }
};
```

The time-based sampling check adds ~25-30 cycles per VM instruction (timer read + RNG + integer arithmetic), but samples only occur roughly every 100μs of execution time rather than every Nth instruction. This provides much better statistical accuracy about where execution time is actually spent. Each thread maintains independent timer and RNG state to avoid cache line contention that would slow down parallel execution.

### Low-overhead histogram storage

Sample collection uses time-based sampling with stochastic rounding to record instruction execution at random points in time. The profiler uses a single histogram array matching the layout of `ProgramParser::m_program_data`, where each byte offset corresponds to one histogram counter. This eliminates the need for program ID mapping and program base address tracking.

```cpp
class LineProfiler {
    static constexpr uint64_t TARGET_SAMPLE_INTERVAL_NS = 100000; // 100μs between samples
    
    // Single histogram covering the entire program data array
    static std::vector<std::atomic<uint64_t>> histogram;
    static const uint8_t* program_data_base;
    
    // Per-thread sampling state  
    thread_local static uint64_t last_sample_time;
    
public:
    static void init(const uint8_t* program_data, size_t size) {
        program_data_base = program_data;
        histogram.resize(size);
        for (auto& counter : histogram) {
            counter.store(0, std::memory_order_relaxed);
        }
    }
    
    static void sample_instruction(Program pc) {
        uint64_t current_time = FastClock::now();
        uint64_t elapsed_ns = current_time - last_sample_time;
        
        // Stochastic rounding: add random dither and divide
        uint64_t random_dither = FastRNG::next() % TARGET_SAMPLE_INTERVAL_NS;
        uint64_t total = elapsed_ns + random_dither;
        uint64_t samples = total / TARGET_SAMPLE_INTERVAL_NS;
        
        if (likely(samples == 0)) return;
        
        // Record sample and update last sample time
        last_sample_time = current_time;
        
        size_t offset = pc - program_data_base;
        if (likely(offset < histogram.size())) {
            histogram[offset].fetch_add(1, std::memory_order_relaxed);
        }
    }
};
```

The direct offset approach is much simpler than tracking separate program IDs. Since `ProgramParser` already stores all programs in a single contiguous array, the profiler uses the same layout for its histogram. The `init()` method gets the base address from `ProgramParser::m_program_data`, and `sample_instruction()` calculates the offset directly as `pc - program_data_base`. This eliminates hash table lookups, program base address tracking, and complex indexing while providing perfect alignment with the existing program storage layout.

### Usage in the virtual machine

The line profiler integrates into the VM execution hot path by sampling at every instruction boundary. Since programs are stored in a single contiguous array, no additional context tracking is needed.

```cpp
// Initialize profiler with program data (in VirtualMachine::load or similar)
void VirtualMachine::load(Signature &signature) {
    // ... existing code ...
    // Initialize line profiler with program data layout
    LineProfiler::init(parser.m_program_data.data(), parser.m_program_data.size());
}

// Modified _execute() in vm_impl.hpp  
void VirtualMachine::_execute(Program program, Context *context) const {
    // Sample instruction execution for line profiling
    LineProfiler::sample_instruction(program);
    
    OpCode op_code = pop_op_code(program);
    // ... rest of execution unchanged
}
```

The integration is extremely simple since the profiler leverages the existing program storage layout. The `sample_instruction()` method is called once per VM instruction with just the program counter, and the profiler calculates the offset directly from the global program data base address.

### Persistence format

Sample data saves to disk in a compact binary format that only stores non-zero counters. The format stores byte offsets into the program data array, which the post-processor maps to line numbers using the same logic as `ProgramParser`.

```
Binary format:
[Header]
- Magic bytes: "POMAGMA_PROFILE\0" (16 bytes)
- Format version: uint32_t
- Sample interval (nanoseconds): uint64_t
- Total time samples collected: uint64_t
- Program data size (bytes): uint64_t

[Sample data]
For each non-zero counter:
- Byte offset: varint64
- Sample count: varint64
```

Variable-length encoding (varint) compresses instruction offsets and counts efficiently. Most instructions have zero samples, so the format only stores non-zero entries. Typical compression ratios reach 10:1 compared to fixed-width arrays.

The profiler writes data periodically during long runs to avoid memory growth and prevent data loss on crashes. Write frequency balances data safety against I/O overhead that could affect timing measurements.

### Postprocessing

A Python script merges binary sample data with `.optimized.programs` files to show execution frequency per instruction. The script maps program addresses from profiler data to line numbers in human-readable assembly files.

```python
# postprocess.py usage
python postprocess.py profile.bin skja.optimized.programs > annotated.programs

# Example output
# plan 65: 4952 bytes, 1,234,567 time samples (94.03% of execution time)
GIVEN_BINARY_RELATION NLESS a b          #         0 (0.0%)
SEQUENCE 16                              #         0 (0.0%) 
LETS_BINARY_RELATION_RHS LESS c b        #   156,789 (12.7%)  ← hotspot
LETS_BINARY_RELATION_LHS NLESS a d       #   234,567 (19.0%)  ← hotspot  
FOR_POS_NEG e c d                        #   789,123 (63.9%)  ← major bottleneck
INFER_BINARY_RELATION NLESS a e          #    54,088 (4.4%)
```

The script also generates summary reports showing the top instruction hotspots across all programs:

```
Top instruction hotspots (by execution time):
1. FOR_POS_NEG e c d (plan 65, offset 24): 789,123 samples (63.9% of time)
2. LETS_BINARY_RELATION_LHS NLESS a d (plan 65, offset 16): 234,567 samples (19.0% of time)  
3. LETS_BINARY_RELATION_RHS LESS c b (plan 65, offset 12): 156,789 samples (12.7% of time)
...
```

Output formats include annotated assembly for human review and CSV data for automated analysis. The post-processor uses the same program parsing logic as Pomagma's existing `ProgramParser` to ensure consistency with VM execution.

## Work plan

- [ ] Add `FastClock` class in `pomagma/util/fast_clock.hpp` with platform-specific timer implementations and thread-local calibration
- [ ] Add `FastRNG` class in `pomagma/util/fast_rng.hpp` using Xorshift algorithm with thread-local state and sampling interface  
- [ ] Add `LineProfiler` class in `pomagma/util/line_profiler.hpp` with single histogram array matching program data layout
- [ ] Modify `VirtualMachine::load()` in `pomagma/atlas/vm_impl.hpp` to initialize `LineProfiler` with program data base address
- [ ] Modify `VirtualMachine::_execute()` in `pomagma/atlas/vm_impl.hpp` to call `LineProfiler::sample_instruction()` on entry
- [ ] Add binary format writer in `LineProfiler` class using varint encoding to save sparse histogram data to disk
- [ ] Create `postprocess_profile.py` script to read binary data and merge with `.optimized.programs` files 
- [ ] Add environment variable `POMAGMA_LINE_PROFILING=1` to enable profiling and set sampling rate configuration
- [ ] Integrate profiler initialization with existing `ProgramProfiler` setup in surveyor and cartographer startup
- [ ] Add profiler data collection to `make profile-cartographer` and `make profile-surveyor` targets with post-processing 