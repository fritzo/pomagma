#pragma once

#include <pomagma/util/util.hpp>
#include <string>
#include <sstream>
#include <iomanip>
#include <vector>
#include <array>
#include <map>

// Assumes one of the following is included:
//#include <pomagma/util/sequential/dense_set.hpp>
//#include <pomagma/util/concurrent/dense_set.hpp>

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

    void add_raw (const void * data, size_t bytes)
    {
        POMAGMA_ASSERT1(m_state == ADDING,
                "adding to Hasher state when finished");
        POMAGMA_ASSERT(
                SHA1_Update(&m_context, data, bytes),
                "SHA1_Update failed");
    }

    void add (const uint8_t & t) { add_raw(&t, 1); }
    void add (const uint16_t & t) { add_raw(&t, 2); }
    void add (const uint32_t & t) { add_raw(&t, 4); }
    void add (const uint64_t & t) { add_raw(&t, 8); }

    void add (const std::vector<uint8_t> & t) { add_raw(&t[0], 1 * t.size()); }
    void add (const std::vector<uint16_t> & t) { add_raw(&t[0], 2 * t.size()); }
    void add (const std::vector<uint32_t> & t) { add_raw(&t[0], 4 * t.size()); }
    void add (const std::vector<uint64_t> & t) { add_raw(&t[0], 8 * t.size()); }

    void add (const std::string & t)
    {
        add_raw(t.data(), t.size());
    }

    template<class T, size_t size>
    void add (const std::array<T, size> & t)
    {
        add_raw(t.data(), size * sizeof(T));
    }

    //template<class DenseSet>
    //void add_set (const DenseSet & t)
    //{
    //    add_raw(t.raw_data(), t.data_size_bytes());
    //}

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

    void add_file (const std::string & filename);

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
        return str(m_data);
    }

    static std::string str (const Digest & digest)
    {
        std::ostringstream o;
        for (int i : digest) {
            o << std::setw(2) << std::hex << std::nouppercase
              << std::setfill('0') << i;
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
};

std::string print_digest (const Hasher::Digest & digest);
Hasher::Digest parse_digest (const std::string & hex);

} // namespace pomagma
