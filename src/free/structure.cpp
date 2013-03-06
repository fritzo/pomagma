#include "structure.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/structure.hpp>

namespace pomagma
{

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

} // namespace pomagma
