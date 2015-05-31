#include "structure_impl.hpp"
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
    pomagma::log_stats(m_signature);
}

} // namespace pomagma
