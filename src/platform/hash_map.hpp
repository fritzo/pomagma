#pragma once

#include <unordered_map>
#include <utility>


// Fowler-Noll-Vo hashing
// http://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function
namespace FNV_hash
{

class HashState
{
    uint64_t m_state;

public:

    HashState () : m_state(0xcbf29ce484222325UL) {}
    void add (const uint64_t & data)
    {
        m_state = (m_state ^ data) * 0x100000001b3UL;
    }
    uint64_t get () { return m_state; }
};

} // namespace FNV_hasher


namespace std
{

template <>
struct hash<pair<uint32_t, uint32_t> >
{
    // TODO should __x be a const references?
    uint32_t operator()(pair<uint32_t, uint32_t> __x) const
    {
        uint32_t x = __x.first;
        uint32_t y = __x.second;
        return (y << 16) ^ (y >> 16) ^ x;
    }
};

template <>
struct hash<pair<uint64_t, uint64_t> >
{
    uint64_t operator()(pair<uint64_t, uint64_t> __x) const
    {
        uint64_t x = __x.first;
        uint64_t y = __x.second;
        return (y << 32) ^ (y >> 32) ^ x;
    }
};

} // namespace std
