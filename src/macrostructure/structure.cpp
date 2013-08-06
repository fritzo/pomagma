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

void Structure::init_carrier (size_t item_dim)
{
    clear();
    m_signature.declare(* new Carrier(item_dim));
}

void Structure::log_stats ()
{
    pomagma::log_stats(m_signature);
}

} // namespace pomagma
