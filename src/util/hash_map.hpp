#pragma once

#include <unordered_map>
#include <utility>

// Fowler-Noll-Vo hashing
// http://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function
namespace FNV_hash {

class HashState
{
    uint64_t m_state;

public:

    HashState () : m_state(0xcbf29ce484222325UL) {}
    void add (const uint64_t & data)
    {
        // FIXME this is wrong in multiple ways
        m_state = (m_state ^ data) * 0x100000001b3UL;
    }
    uint64_t get () { return m_state; }
};

} // namespace FNV_hasher
