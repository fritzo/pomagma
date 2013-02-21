#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/util/dense_set.hpp>
#include <string>
#include <sstream>
#include <iomanip>
#include <vector>
#include <map>

// http://www.openssl.org/docs/crypto/sha.html
extern "C" {
#include <openssl/sha.h>
}

namespace pomagma
{

class Hasher
{
public:

    typedef std::vector<uint8_t> Digest;
    typedef std::map<std::string, Digest> Dict;

    Hasher ()
        : m_state(ADDING),
          m_data(SHA_DIGEST_LENGTH, 0)
    {
        POMAGMA_ASSERT(SHA1_Init(&m_context), "SHA1_Init failed");
    }

    void add (const uint8_t & t) { update(&t, 1); }
    void add (const uint16_t & t) { update(&t, 2); }
    void add (const uint32_t & t) { update(&t, 4); }
    void add (const uint64_t & t) { update(&t, 8); }

    void add (const std::vector<uint8_t> & t) { update(&t[0], 1 * t.size()); }
    void add (const std::vector<uint16_t> & t) { update(&t[0], 2 * t.size()); }
    void add (const std::vector<uint32_t> & t) { update(&t[0], 4 * t.size()); }
    void add (const std::vector<uint64_t> & t) { update(&t[0], 8 * t.size()); }

    void add (const std::string & t)
    {
        update(t.data(), t.size());
    }

    void add (const DenseSet & t)
    {
        update(t.raw_data(), t.data_size_bytes());
    }

    void add (const std::vector<Digest> & t)
    {
        for (const auto & i : t) {
            add(i);
        }
    }

    void add (const Dict & t)
    {
        for (const auto & i : t) {
            add(i.first);
            add(i.second);
        }
    }

    const Digest & finish ()
    {
        POMAGMA_ASSERT1(m_state == ADDING,
                "finishing a Hasher state when already finished");

        POMAGMA_ASSERT(
                SHA1_Final(&m_data[0], &m_context),
                "SHA1_Final failed");

        m_state = FINISHED;
        return m_data;
    }

    const Digest & data () const
    {
        POMAGMA_ASSERT1(m_state == FINISHED,
                "reading a Hasher state when not finished");
        return m_data;
    }


    std::string str () const
    {
        POMAGMA_ASSERT(m_state == FINISHED,
                "printing a Hasher when not finished");

        std::ostringstream o;
        for (int i : m_data) {
            o << std::setw(2) << std::hex << std::setfill('0') << i;
        }
        return o.str();
    }

    template<class T>
    static Digest digest (const T & t)
    {
        Hasher hasher;
        hasher.add(t);
        return hasher.finish();
    }

private:

    SHA_CTX m_context;
    enum State { ADDING, FINISHED };
    State m_state;
    Digest m_data;

    void update (const void * data, size_t bytes)
    {
        POMAGMA_ASSERT1(m_state == ADDING,
                "adding to Hasher state when finished");
        POMAGMA_ASSERT(
                SHA1_Update(&m_context, data, bytes),
                "SHA1_Update failed");
    }
};

} // namespace pomagma
