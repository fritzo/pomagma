#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/atlas/signature.hpp>

namespace pomagma
{

class Structure : noncopyable
{
    Signature m_signature;

public:

    Structure () {}

    Signature & signature () { return m_signature; }
    Carrier & carrier () { return * m_signature.carrier(); }

    void validate_consistent ();
    void validate ();
    void clear ();
    void load (const std::string & filename);
    void dump (const std::string & filename);
    void log_stats ();
};

} // namespace pomagma
