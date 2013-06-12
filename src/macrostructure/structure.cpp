#include "structure.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/platform/structure.hpp>

namespace pomagma
{

void Structure::validate_consistent ()
{
    pomagma::validate_consistent(m_signature);
}

void Structure::validate ()
{
    pomagma::validate(m_signature);
}

void Structure::clear ()
{
    pomagma::clear(m_signature);
}

void Structure::load (const std::string & filename, size_t extra_item_dim)
{
    clear();
    pomagma::load(m_signature, filename, extra_item_dim);
}

void Structure::dump (const std::string & filename)
{
    pomagma::dump(signature(), filename);
}

void Structure::init_signature (Structure & other, size_t item_dim)
{
    clear();
    m_signature.declare(* new Carrier(item_dim));
    for (auto i : other.signature().binary_relations()) {
        m_signature.declare(i.first, * new BinaryRelation(carrier()));
    }
    for (auto i : other.signature().nullary_functions()) {
        m_signature.declare(i.first, * new NullaryFunction(carrier()));
    }
    for (auto i : other.signature().injective_functions()) {
        m_signature.declare(i.first, * new InjectiveFunction(carrier()));
    }
    for (auto i : other.signature().binary_functions()) {
        m_signature.declare(i.first, * new BinaryFunction(carrier()));
    }
    for (auto i : other.signature().symmetric_functions()) {
        m_signature.declare(i.first, * new SymmetricFunction(carrier()));
    }
}

} // namespace pomagma
