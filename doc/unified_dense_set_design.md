# Unified DenseSet Design

## Objective
Create a single DenseSet class that can be used with both atomic and non-atomic access patterns through compile-time method selection, enabling zero-overhead performance optimization in different contexts.

## Background

### Performance Critical Requirements
DenseSet operations appear in tight inference loops where `SetIterator<Set>::next()` is profiled as "one of the slowest methods." Any unified design must preserve current performance characteristics with zero runtime overhead - no virtual dispatch, no runtime conditionals, no additional memory indirection.

### Current Implementation Analysis
Both `concurrent::DenseSet` and `sequential::DenseSet` use identical memory layouts (word-aligned bitfields) with the same core algorithms. The only difference is `std::atomic<Word>` vs `Word` storage and corresponding `bool_ref` implementations. Operations like `contains()`, `insert()`, and `iter()` have identical logic but different memory access patterns.

### Static Context Knowledge
Applications know statically which access pattern they need: surveyor's OpenMP threads can use atomic operations for shared data and direct operations for thread-local temporaries. The choice between atomic/non-atomic is determined by data ownership and thread safety requirements, not runtime conditions.

### Memory Layout Compatibility  
Since `std::atomic<T>` has the same memory layout and alignment as `T`, the same memory allocation can be safely accessed through both `Word*` and `std::atomic<Word>*` pointers, provided access is properly synchronized at context boundaries.

## Design Overview
A union-based DenseSet stores both `Word*` and `std::atomic<Word>*` pointers to the same memory, with separate method families for atomic and non-atomic access. Applications choose `atomic_contains()` vs `direct_contains()` based on static context knowledge. Context switching occurs at explicit synchronization points using memory barriers, with zero runtime overhead for operations within each context.

```cpp
class DenseSet {
    union {
        Word* m_direct_words;
        std::atomic<Word>* m_atomic_words;
    };
    
public:
    // Atomic operations - for concurrent contexts
    bool atomic_contains(size_t i) const;
    void atomic_insert(size_t i);
    
    // Direct operations - for sequential contexts  
    bool direct_contains(size_t i) const;
    void direct_insert(size_t i);
    
    // Context switching with explicit barriers
    void sync_to_direct_context();
    void sync_to_atomic_context();
};
```

## Design Details

### Union Storage with Dual Access Methods
The unified DenseSet uses a union to provide typed access to the same memory through atomic and non-atomic pointers. Each operation has both `atomic_*` and `direct_*` variants that compile to identical performance as the current separate implementations.

```cpp
class DenseSet : noncopyable {
    const size_t m_item_dim;
    const size_t m_word_dim;
    
    union {
        Word* m_direct_words;
        std::atomic<Word>* m_atomic_words;  
    };
    const bool m_alias;
    
public:
    explicit DenseSet(size_t item_dim);
    
    // Atomic operations - zero overhead vs concurrent::DenseSet
    bool atomic_contains(size_t i) const {
        return concurrent::bool_ref::index(m_atomic_words, i);
    }
    void atomic_insert(size_t i) {
        concurrent::bool_ref::index(m_atomic_words, i).one();
    }
    
    // Direct operations - zero overhead vs sequential::DenseSet  
    bool direct_contains(size_t i) const {
        return sequential::bool_ref::index(m_direct_words, i);
    }
    void direct_insert(size_t i) {
        sequential::bool_ref::index(m_direct_words, i).one();
    }
};
```

### Context Synchronization Protocol
Context switches happen at explicit application-controlled points using memory barriers. Applications must ensure proper synchronization when transitioning between atomic and direct access patterns.

```cpp
void DenseSet::sync_to_direct_context() {
    // Ensure all atomic operations complete before direct access
    std::atomic_thread_fence(std::memory_order_seq_cst);
}

void DenseSet::sync_to_atomic_context() {
    // Ensure all direct writes visible before atomic access
    std::atomic_thread_fence(std::memory_order_seq_cst);
}
```

Applications coordinate context switches through existing synchronization mechanisms (OpenMP barriers, mutexes) combined with these explicit sync calls.

### Iterator Variants for Each Context
Set iteration provides separate iterator types for atomic and direct contexts, maintaining zero-overhead performance for each access pattern.

```cpp
class DenseSet {
public:
    // Atomic context iterators
    typedef SetIterator<concurrent::Intersection<1>> AtomicIterator;
    typedef SetIterator<concurrent::Intersection<2>> AtomicIterator2;
    
    AtomicIterator atomic_iter() const {
        return AtomicIterator(m_item_dim, m_atomic_words);
    }
    
    // Direct context iterators  
    typedef SetIterator<sequential::Intersection<1>> DirectIterator;
    typedef SetIterator<sequential::Intersection<2>> DirectIterator2;
    
    DirectIterator direct_iter() const {
        return DirectIterator(m_item_dim, m_direct_words);
    }
};
```

### Set Operations for Each Context
Complex set operations (`set_insn`, `operator+=`, etc.) have atomic and direct variants that compile to optimal code for each context.

```cpp
// Atomic context set operations
void atomic_set_insn(const DenseSet& lhs, const DenseSet& rhs) {
    for (size_t i = 0; i < m_word_dim; ++i) {
        Word lhs_word = lhs.m_atomic_words[i].load(std::memory_order_relaxed);
        Word rhs_word = rhs.m_atomic_words[i].load(std::memory_order_relaxed);
        m_atomic_words[i].store(lhs_word & rhs_word, std::memory_order_relaxed);
    }
}

// Direct context set operations - enables SIMD vectorization
void direct_set_insn(const DenseSet& lhs, const DenseSet& rhs) {
    for (size_t i = 0; i < m_word_dim; ++i) {
        m_direct_words[i] = lhs.m_direct_words[i] & rhs.m_direct_words[i];
    }
}
```

### Surveyor Usage Pattern Example
The design enables surveyor to optimize thread-local operations while maintaining safety for shared data:

```cpp
void infer_nless_monotone(/* ... */) {
    DenseSet z_set(item_dim);  // Thread-local temporary
    
    #pragma omp parallel
    {
        // Use direct operations for thread-local intensive computation
        z_set.sync_to_direct_context();
        z_set.direct_set_insn(fun.get_Lx_set(x), fun.get_Lx_set(y));
        
        for (auto iter = z_set.direct_iter(); iter.ok(); iter.next()) {
            Ob z = *iter;
            // ... computation ...
        }
        
        #pragma omp barrier  // Synchronize before shared access
        
        // Switch to atomic context for shared updates
        z_set.sync_to_atomic_context();
        if (condition) {
            NLESS->atomic_insert(x, y);  // Shared data structure
        }
    }
}
```

### Backward Compatibility Strategy
Type aliases preserve existing interfaces while enabling gradual migration:

```cpp
namespace concurrent {
    using DenseSet = ::pomagma::DenseSet;  // Use atomic_ methods
}

namespace sequential {  
    using DenseSet = ::pomagma::DenseSet;  // Use direct_ methods
}
```

Existing code continues working with no changes, while new code can leverage dual-context capabilities.

### Memory Management Integration
The unified design preserves existing memory management patterns through the shared allocation strategy:

```cpp
DenseSet::DenseSet(size_t item_dim) 
    : m_item_dim(item_dim),
      m_word_dim(items_to_words(item_dim)),
      m_alias(false) {
    
    // Single allocation, dual access
    void* memory = malloc_blocks(m_word_dim);
    m_direct_words = static_cast<Word*>(memory);
    // m_atomic_words points to same memory through union
}
```

### Performance Validation Requirements
The design must validate zero performance regression through benchmarks comparing:
1. Current `concurrent::DenseSet` vs unified `atomic_*` methods
2. Current `sequential::DenseSet` vs unified `direct_*` methods  
3. Memory overhead and allocation patterns
4. Compiler optimization effectiveness for vectorization

## Work Plan

- [ ] Implement union-based storage with `Word*` and `std::atomic<Word>*` accessing the same memory allocation
- [ ] Create dual method families (`atomic_*` and `direct_*`) for all DenseSet operations with zero-overhead implementations
- [ ] Add explicit context synchronization methods using memory barriers for safe transitions between access patterns
- [ ] Implement separate iterator types (`AtomicIterator`, `DirectIterator`) maintaining current performance characteristics  
- [ ] Create dual variants of set operations (`atomic_set_insn`, `direct_set_insn`) enabling vectorization in direct context
- [ ] Add type aliases for backward compatibility with existing `concurrent::` and `sequential::` namespaced usage
- [ ] Implement comprehensive performance benchmarks validating zero overhead vs current separate implementations
- [ ] Update `surveyor/infer.cpp` to demonstrate thread-local direct context usage with shared atomic context coordination
- [ ] Add memory barrier placement guidelines and best practices documentation for application developers
- [ ] Create migration guide showing how existing code can adopt unified DenseSet while preserving performance