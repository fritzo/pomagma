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
    pomagma::clear_data(m_signature);
}

void Structure::load (const std::string & filename)
{
    clear();
    pomagma::load_data(m_signature, filename);
}

void Structure::dump (const std::string & filename)
{
    pomagma::dump(signature(), filename);
}

void Structure::log_stats ()
{
    carrier().log_stats();

    for (auto pair : m_signature.binary_relations()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : m_signature.nullary_functions()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : m_signature.injective_functions()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : m_signature.binary_functions()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : m_signature.symmetric_functions()) {
        pair.second->log_stats(pair.first);
    }
}

} // namespace pomagma
