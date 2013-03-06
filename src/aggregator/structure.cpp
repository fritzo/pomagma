#include "structure.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/structure.hpp>
#include <pomagma/util/hdf5.hpp>

namespace pomagma
{

void Structure::clear ()
{
    pomagma::clear(m_signature);
}

void Structure::load (const std::string & filename, size_t extra_item_dim)
{
    POMAGMA_INFO("Loading structure from file " << filename);
    clear();
    // TODO move all hdf5 stuff to util/structure.hpp
    hdf5::init();
    hdf5::InFile file(filename);
    pomagma::load(m_signature, file, extra_item_dim);
}

void Structure::dump (const std::string & filename)
{
    POMAGMA_INFO("Dumping structure to file " << filename);
    hdf5::init();
    hdf5::OutFile file(filename);
    pomagma::dump(signature(), file);
}

} // namespace pomagma
