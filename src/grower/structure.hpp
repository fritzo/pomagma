#pragma once

#include "util.hpp"
#include "signature.hpp"
#include <map>

typedef int hid_t;

namespace pomagma
{

class Structure : public Signature::Observer
{
    Carrier & m_carrier;

    std::map<std::string, BinaryRelation *> m_binary_relations;
    std::map<std::string, NullaryFunction *> m_nullary_functions;
    std::map<std::string, InjectiveFunction *> m_injective_functions;
    std::map<std::string, BinaryFunction *> m_binary_functions;
    std::map<std::string, SymmetricFunction *> m_symmetric_functions;

public:

    Structure (Signature & signature)
        : Signature::Observer(signature),
          m_carrier(signature.carrier())
    {}

    void declare (const std::string & name, BinaryRelation & rel);
    void declare (const std::string & name, NullaryFunction & fun);
    void declare (const std::string & name, InjectiveFunction & fun);
    void declare (const std::string & name, BinaryFunction & fun);
    void declare (const std::string & name, SymmetricFunction & fun);

    void load (const std::string & filename);
    void dump (const std::string & filename);

private:

    void load_binary_relations (const hid_t & file_id);
    void load_nullary_functions (const hid_t & file_id);
    void load_injective_functions (const hid_t & file_id);
    void load_binary_functions (const hid_t & file_id);
    void load_symmetric_functions (const hid_t & file_id);

    void dump_binary_relations (const hid_t & file_id);
    void dump_nullary_functions (const hid_t & file_id);
    void dump_injective_functions (const hid_t & file_id);
    void dump_binary_functions (const hid_t & file_id);
    void dump_symmetric_functions (const hid_t & file_id);
};

} // namespace pomagma
