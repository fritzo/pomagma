#include "structure.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

extern "C" {
#include <hdf5.h>
}

namespace pomagma
{

//----------------------------------------------------------------------------
// construction

void Structure::declare (const std::string & name, BinaryRelation & rel)
{
    m_binary_relations[name] = & rel;
}

void Structure::declare (const std::string & name, NullaryFunction & fun)
{
    m_nullary_functions[name] = & fun;
}

void Structure::declare (const std::string & name, InjectiveFunction & fun)
{
    m_injective_functions[name] = & fun;
}

void Structure::declare (const std::string & name, BinaryFunction & fun)
{
    m_binary_functions[name] = & fun;
}

void Structure::declare (const std::string & name, SymmetricFunction & fun)
{
    m_symmetric_functions[name] = & fun;
}

//----------------------------------------------------------------------------
// persistence

// adapted from
// http://www.hdfgroup.org/HDF5/Tutor/crtfile.html

void Structure::load (const std::string & filename)
{
    herr_t status;

    // Open file
    hid_t file_id = H5Fopen(filename.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);
    POMAGMA_ASSERT(file_id, "failed to open file " << filename);

    // TODO do this in parallel
    load_binary_relations(file_id);
    load_nullary_functions(file_id);
    load_injective_functions(file_id);
    load_binary_functions(file_id);
    load_symmetric_functions(file_id);

    // Close file
    status = H5Fclose(file_id);
    herr_t FIXME = 0;
    POMAGMA_ASSERT(status == FIXME, "failed to close file");
}

void Structure::load_binary_relations (const hid_t & file_id __attribute__((unused)))
{
    TODO("load binary relations");
}

void Structure::load_nullary_functions (const hid_t & file_id __attribute__((unused)))
{
    TODO("load nullary functions");
}

void Structure::load_injective_functions (const hid_t & file_id __attribute__((unused)))
{
    TODO("load injective functions");
}

void Structure::load_binary_functions (const hid_t & file_id)
{
    herr_t status;
    herr_t FIXME = 0;

    const std::string prefix = "/function/binary/";
    for (const auto & pair : m_binary_functions) {
        std::string name = prefix + pair.first;
        BinaryFunction * fun = pair.second;

        // Create the dataset
        hid_t dataset_id = H5Dopen(
                file_id,
                name.c_str()
                //, H5P_DEFAULT
                );

        status = H5Dread(
                dataset_id,
                H5T_NATIVE_USHORT, // 16-bit, or should this be H5T_NATIVE_INT
                H5S_ALL,
                H5S_ALL,
                H5P_DEFAULT,
                fun->raw_data());
        POMAGMA_ASSERT(status == FIXME, "failed to read " << name);

        // End access to the dataset and release resources used by it
        status = H5Dclose(dataset_id);
        POMAGMA_ASSERT(status == FIXME, "failed to close " << name);
    }
}

void Structure::load_symmetric_functions (const hid_t & file_id __attribute__((unused)))
{
    TODO("load symmetric functions");
}

void Structure::dump (const std::string & filename)
{
    herr_t status;
    herr_t FIXME = 0;

    // Create a new file using default properties
    hid_t file_id = H5Fcreate(
            filename.c_str(),
            H5F_ACC_TRUNC,  // creation mode
            H5P_DEFAULT,    // creation property list
            H5P_DEFAULT);   // access property list
    POMAGMA_ASSERT(file_id, "failed to open file " << filename);

    // TODO do this in parallel
    dump_binary_relations(file_id);
    dump_nullary_functions(file_id);
    dump_injective_functions(file_id);
    dump_binary_functions(file_id);
    dump_symmetric_functions(file_id);

    // Terminate access to the file
    status = H5Fclose(file_id);
    POMAGMA_ASSERT(status == FIXME, "failed to close file");
}

void Structure::dump_binary_relations (const hid_t & file_id __attribute__((unused)))
{
    TODO("dump binary relations");
}

void Structure::dump_nullary_functions (const hid_t & file_id __attribute__((unused)))
{
    TODO("dump nullary functions");
}

void Structure::dump_injective_functions (const hid_t & file_id)
{
    herr_t status;
    herr_t FIXME = 0;

    // Create the data space for the dataset
    const size_t item_dim = m_carrier.item_dim();
    hsize_t dims[] = {item_dim};
    hid_t dataspace_id = H5Screate_simple(1, dims, NULL);

    const std::string prefix = "/function/injective/";
    for (const auto & pair : m_binary_functions) {
        std::string name = prefix + pair.first;
        const BinaryFunction * fun = pair.second;

        // Create the dataset
        hid_t dataset_id = H5Dcreate(
                file_id,
                name.c_str(),
                H5T_STD_U32LE, // 32-bit
                dataspace_id,
                H5P_DEFAULT
                //, H5P_DEFAULT
                //, H5P_DEFAULT
                );

        static_assert(sizeof(Ob) == 2, "H5 datatype does not match size");
        hid_t native_ob = H5T_NATIVE_USHORT;
        status = H5Dwrite(
                dataset_id,
                native_ob,
                H5S_ALL,
                H5S_ALL,
                H5P_DEFAULT,
                fun->raw_data());
        POMAGMA_ASSERT(status == FIXME, "failed to write " << name);

        // End access to the dataset and release resources used by it
        status = H5Dclose(dataset_id);
        POMAGMA_ASSERT(status == FIXME, "failed to close " << name);
    }

    // Terminate access to the data space
    status = H5Sclose(dataspace_id);
}

void Structure::dump_binary_functions (const hid_t & file_id)
{
    herr_t status;
    herr_t FIXME = 0;

    // Create the data space for the dataset
    const size_t item_dim = m_carrier.item_dim();
    hsize_t dims[] = {item_dim, item_dim};
    hid_t dataspace_id = H5Screate_simple(2, dims, NULL);

    const std::string prefix = "/function/binary/";
    for (const auto & pair : m_binary_functions) {
        std::string name = prefix + pair.first;
        const BinaryFunction * fun = pair.second;

        // Create the dataset
        hid_t dataset_id = H5Dcreate(
                file_id,
                name.c_str(),
                H5T_STD_U32LE, // 32-bit
                dataspace_id,
                H5P_DEFAULT
                //, H5P_DEFAULT
                //, H5P_DEFAULT
                );

        // TODO loop over blocks, using H5 hyperslab selection
        // http://www.hdfgroup.org/HDF5/Tutor/selectsimple.html
        static_assert(sizeof(Ob) == 2, "H5 datatype does not match size");
        hid_t native_ob = H5T_NATIVE_USHORT;
        status = H5Dwrite(
                dataset_id,
                native_ob,
                H5S_ALL,
                H5S_ALL,
                H5P_DEFAULT,
                fun->raw_data());
        POMAGMA_ASSERT(status == FIXME, "failed to write " << name);

        // End access to the dataset and release resources used by it
        status = H5Dclose(dataset_id);
        POMAGMA_ASSERT(status == FIXME, "failed to close " << name);
    }

    // Terminate access to the data space
    status = H5Sclose(dataspace_id);
}

void Structure::dump_symmetric_functions (const hid_t & file_id __attribute__((unused)))
{
    TODO("dump symmetric functions");
}

} // namespace pomagma
