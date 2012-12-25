#include "structure.hpp"
extern "C" {
#include <hdf5.h>
}

// adapted from
// http://www.hdfgroup.org/HDF5/Tutor/crtfile.html

void Structure::load (const std::string & filename)
{
    herr_t status;

    // Open file
    hid_t file_id = H5Fopen(filename.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);
    POMAGMA_ASSERT(file_id, "failed to open file " << filename);

    TODO("read data");

    // Close file
    status = H5Fclose(file_id);
}

void Structure::dump (const std::string & filename)
{
    herr_t status;

    // Create a new file using default properties
    hid_t file_id = H5Fcreate(
            filename.c_str(),
            H5F_ACC_TRUNC,  // creation mode
            H5P_DEFAULT,    // creation property list
            H5P_DEFAULT);   // access property list
    POMAGMA_ASSERT(file_id, "failed to open file " << filename);

    dump_nullary_functions(file_id);
    dump_injective_functions(file_id);
    dump_binary_functions(file_id);
    dump_symmetric_functions(file_id);

    // Terminate access to the file
    status = H5Fclose(file_id);
}

void Structure::load_binary_functions (const hid_t & file_id)
{
    const std::string prefix = "/function/binary/"
    for (const auto & pair : m_binary_functions) {
        std::string name = prefix + pair.first;
        BinaryFunction * fun = pair.second;

        // Create the dataset
        hid_t dataset_id = H5Dopen(
                file_id,
                name.c_str(),
                H5P_DEFAULT);

        status = H5Dread(
                dataset_id,
                H5T_NATIVE_U16, // 16-bit, or should this be H5T_NATIVE_INT
                H5S_ALL,
                H5S_ALL,
                H5P_DEFAULT,
                fun->raw_data());

        // End access to the dataset and release resources used by it
        status = H5Dclose(dataset_id);
    }
}

void Structure::dump_injective_functions (const hid_t & file_id)
{
    // Create the data space for the dataset
    const size_t item_dim = m_carrier.item_dim();
    hsize_t dims[] = {item_dim};
    hid_t dataspace_id = H5Screate_simple(1, dims, NULL);

    const std::string prefix = "/function/binary/"
    for (const auto & pair : m_binary_functions) {
        std::string name = prefix + pair.first;
        const BinaryFunction * fun = pair.second;

        // Create the dataset
        hid_t dataset_id = H5Dcreate(
                file_id,
                name.c_str(),
                H5T_STD_U32LE, // 32-bit
                dataspace_id,
                H5P_DEFAULT,
                H5P_DEFAULT,
                H5P_DEFAULT);

        static_assert(sizeof(Ob) == 16, "H5 datatype does not match size");
        hid_t native_ob = H5T_NATIVE_USHORT;
        status = H5Dwrite(
                dataset_id,
                native_ob,
                H5S_ALL,
                H5S_ALL,
                H5P_DEFAULT,
                fun->raw_data());

        // End access to the dataset and release resources used by it
        status = H5Dclose(dataset_id);
    }

    // Terminate access to the data space
    status = H5Sclose(dataspace_id);
}
void Structure::dump_binary_functions (const hid_t & file_id)
{
    // Create the data space for the dataset
    const size_t item_dim = m_carrier.item_dim();
    hsize_t dims[] = {item_dim, item_dim};
    hid_t dataspace_id = H5Screate_simple(2, dims, NULL);

    const std::string prefix = "/function/binary/"
    for (const auto & pair : m_binary_functions) {
        std::string name = prefix + pair.first;
        const BinaryFunction * fun = pair.second;

        // Create the dataset
        hid_t dataset_id = H5Dcreate(
                file_id,
                name.c_str(),
                H5T_STD_U32LE, // 32-bit
                dataspace_id,
                H5P_DEFAULT,
                H5P_DEFAULT,
                H5P_DEFAULT);

        // TODO loop over blocks, using H5 hyperslab selection
        // http://www.hdfgroup.org/HDF5/Tutor/selectsimple.html
        static_assert(sizeof(Ob) == 16, "H5 datatype does not match size");
        hid_t native_ob = H5T_NATIVE_USHORT;
        status = H5Dwrite(
                dataset_id,
                native_ob,
                H5S_ALL,
                H5S_ALL,
                H5P_DEFAULT,
                fun->raw_data());

        // End access to the dataset and release resources used by it
        status = H5Dclose(dataset_id);
    }

    // Terminate access to the data space
    status = H5Sclose(dataspace_id);
}
