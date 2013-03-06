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
    ~Structure () { clear(); }

    Signature & signature () { return m_signature; }
    Carrier & carrier () { return * m_signature.carrier(); }

    void clear ();
    void load (const std::string & filename, size_t extra_item_dim = 0);
    void dump (const std::string & filename);
    bool try_merge (Structure & other); // TODO this belongs elsewhere

private:

    void load_carrier (hdf5::InFile & file, size_t extra_item_dim);
    void load_binary_relations (hdf5::InFile & file);
    void load_nullary_functions (hdf5::InFile & file);
    void load_injective_functions (hdf5::InFile & file);
    void load_binary_functions (hdf5::InFile & file);
    void load_symmetric_functions (hdf5::InFile & file);
};

} // namespace pomagma
