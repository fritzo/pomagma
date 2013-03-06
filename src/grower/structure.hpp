#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/util/signature.hpp>

namespace pomagma
{

namespace hdf5
{
class InFile;
class OutFile;
};

class Structure : noncopyable
{
    Signature m_signature;

public:

    Structure () {}

    Signature & signature () { return m_signature; }
    Carrier & carrier () { return * m_signature.carrier(); }

    void clear ();
    void load (const std::string & filename);
    void dump (const std::string & filename);

private:

    void load_carrier (hdf5::InFile & file);
    void load_binary_relations (hdf5::InFile & file);
    void load_nullary_functions (hdf5::InFile & file);
    void load_injective_functions (hdf5::InFile & file);
    void load_binary_functions (hdf5::InFile & file);
    void load_symmetric_functions (hdf5::InFile & file);
};

} // namespace pomagma
