#pragma once

#include "util.hpp"
#include "signature.hpp"
#include "hasher.hpp"
#include <map>

namespace pomagma
{

namespace hdf5
{
struct InFile;
struct OutFile;
};

class Structure : public Signature::Observer
{
    Carrier & m_carrier;

    std::map<std::string, BinaryRelation *> m_binary_relations;
    std::map<std::string, NullaryFunction *> m_nullary_functions;
    std::map<std::string, InjectiveFunction *> m_injective_functions;
    std::map<std::string, BinaryFunction *> m_binary_functions;
    std::map<std::string, SymmetricFunction *> m_symmetric_functions;

public:

    Structure (Signature & signature);

    void declare (const std::string & name, BinaryRelation & rel);
    void declare (const std::string & name, NullaryFunction & fun);
    void declare (const std::string & name, InjectiveFunction & fun);
    void declare (const std::string & name, BinaryFunction & fun);
    void declare (const std::string & name, SymmetricFunction & fun);

    void clear ();
    void load (const std::string & filename);
    void dump (const std::string & filename);

private:

    Hasher::Digest load_carrier (hdf5::InFile & file);
    Hasher::Digest load_binary_relations (hdf5::InFile & file);
    Hasher::Digest load_nullary_functions (hdf5::InFile & file);
    Hasher::Digest load_injective_functions (hdf5::InFile & file);
    Hasher::Digest load_binary_functions (hdf5::InFile & file);
    Hasher::Digest load_symmetric_functions (hdf5::InFile & file);

    Hasher::Digest dump_carrier (hdf5::OutFile & file);
    Hasher::Digest dump_binary_relations (hdf5::OutFile & file);
    Hasher::Digest dump_nullary_functions (hdf5::OutFile & file);
    Hasher::Digest dump_injective_functions (hdf5::OutFile & file);
    Hasher::Digest dump_binary_functions (hdf5::OutFile & file);
    Hasher::Digest dump_symmetric_functions (hdf5::OutFile & file);
};

} // namespace pomagma
