#include "structure.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/platform/structure.hpp>

namespace pomagma
{

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

} // namespace pomagma
