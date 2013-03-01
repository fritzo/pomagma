#pragma once

#include "util.hpp"
#include <pomagma/util/signature.hpp>

namespace pomagma
{

namespace hdf5
{
struct InFile;
struct OutFile;
};

class Structure : noncopyable
{
    Signature & m_signature;

public:

    Structure (Signature & signature);

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

    void dump_carrier (hdf5::OutFile & file);
    void dump_binary_relations (hdf5::OutFile & file);
    void dump_nullary_functions (hdf5::OutFile & file);
    void dump_injective_functions (hdf5::OutFile & file);
    void dump_binary_functions (hdf5::OutFile & file);
    void dump_symmetric_functions (hdf5::OutFile & file);
};

} // namespace pomagma
