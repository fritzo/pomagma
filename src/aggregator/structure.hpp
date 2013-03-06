#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/util/signature.hpp>

namespace pomagma
{

class Structure : noncopyable
{
    Signature m_signature;

public:

    Structure () {}

    Signature & signature () { return m_signature; }
    Carrier & carrier () { return * m_signature.carrier(); }

    void clear ();
    void load (const std::string & filename, size_t extra_item_dim = 0);
    void dump (const std::string & filename);
};

} // namespace pomagma
