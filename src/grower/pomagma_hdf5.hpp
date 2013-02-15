#include "util.hpp"

extern "C" {
#include <hdf5.h>
}

namespace pomagma
{

namespace hdf5
{

inline void init ()
{
    // permanently turn off error reporting to stderr
    // http://www.hdfgroup.org/HDF5/doc/UG/UG_frame13ErrorHandling.html
    H5Eset_auto(nullptr, nullptr);
}

//----------------------------------------------------------------------------
// Errors
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5E.html

std::string get_error ()
{
    std::string message(4096, '\0');
    FILE * file = fmemopen(&message[0], message.size(), "w");
    POMAGMA_ASSERT(file, "failed to open error message buffer");
    H5Eprint(file);
    fclose(file);
    return message;
}

#define POMAGMA_HDF5_OK(status) POMAGMA_ASSERT(status, get_error())

//----------------------------------------------------------------------------
// Datatypes
// http://www.hdfgroup.org/HDF5/doc/UG/11_Datatypes.html

template<class T>struct Unsigned;

template<> struct Unsigned<uint8_t>
{
    static hid_t id () { return H5T_NATIVE_UCHAR; }
};

template<> struct Unsigned<uint16_t>
{
    static hid_t id () { return H5T_NATIVE_USHORT; }
};

template<> struct Unsigned<uint32_t>
{
    static hid_t id () { return H5T_NATIVE_UINT; }
};

template<> struct Unsigned<uint64_t>
{
    static hid_t id () { return H5T_NATIVE_ULONG; }
};

template<class T>struct Bitfield;

template<> struct Bitfield<uint8_t>
{
    static hid_t id () { return H5T_NATIVE_B8; }
};

template<> struct Bitfield<uint16_t>
{
    static hid_t id () { return H5T_NATIVE_B16; }
};

template<> struct Bitfield<uint32_t>
{
    static hid_t id () { return H5T_NATIVE_B32; }
};

template<> struct Bitfield<uint64_t>
{
    static hid_t id () { return H5T_NATIVE_B64; }
};

//----------------------------------------------------------------------------
// Files
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5F.html

struct InFile : noncopyable
{
    const hid_t id;

    InFile (const std::string & filename)
        : id(H5Fopen(
                    filename.c_str(),
                    H5F_ACC_RDONLY,
                    H5P_DEFAULT))
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to open file " << filename << "\n" << get_error());
    }
    ~InFile ()
    {
        POMAGMA_HDF5_OK(H5Fclose(id));
    }
};

struct OutFile : noncopyable
{
    const hid_t id;

    OutFile (const std::string & filename)
        : id(H5Fcreate(
                    filename.c_str(),
                    H5F_ACC_TRUNC,  // creation mode
                    H5P_DEFAULT,    // creation property list
                    H5P_DEFAULT))   // access property list
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to create file " << filename << "\n" << get_error());
    }
    ~OutFile ()
    {
        POMAGMA_HDF5_OK(H5Fclose(id));
    }
};

//----------------------------------------------------------------------------
// Dataspaces
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5S.html

class Dataset;

struct Dataspace : noncopyable
{
    hid_t id;

    Dataspace ()
    {
        id = H5Screate(H5S_SCALAR);
        POMAGMA_ASSERT(id >= 0, "failed to create dataspace\n" << get_error());
    }

    Dataspace (hsize_t dim)
    {
        int rank = 1;
        hsize_t dims[] = {dim};
        id = H5Screate_simple(rank, dims, nullptr);
        POMAGMA_ASSERT(id >= 0, "failed to create dataspace\n" << get_error());
    }

    Dataspace (hsize_t dim1, hsize_t dim2)
    {
        int rank = 2;
        hsize_t dims[] = {dim1, dim2};
        id = H5Screate_simple(rank, dims, nullptr);
        POMAGMA_ASSERT(id >= 0, "failed to create dataspace\n" << get_error());
    }

    Dataspace (Dataset & dataset);

    ~Dataspace ()
    {
        POMAGMA_HDF5_OK(H5Sclose(id));
    }

    size_t rank () const
    {
        return H5Sget_simple_extent_ndims(id);
    }

    std::vector<hsize_t> shape () const
    {
        size_t ndims = rank();
        std::vector<hsize_t> dims(ndims, 0);
        std::vector<hsize_t> maxdims(ndims, 0);
        POMAGMA_HDF5_OK(H5Sget_simple_extent_dims(
                    id,
                    &dims[0],
                    &maxdims[0]));

        return dims; // discard maxdims
    }

    size_t volume () const
    {
        size_t count = 1;
        for (size_t dim : shape()) {
            count *= dim;
        }
        return count;
    }

    // http://www.hdfgroup.org/ftp/HDF5/examples/introductory/C/h5_subset.c
    void select_hyperslab (const hsize_t offset[], const hsize_t count[])
    {
        POMAGMA_HDF5_OK(H5Sselect_hyperslab(
                id,
                H5S_SELECT_SET,
                offset,
                nullptr, // stride
                count,
                nullptr)); // block
    }

    void select_block (hsize_t offset, hsize_t count)
    {
        select_hyperslab(&offset, &count);
    }
};

//----------------------------------------------------------------------------
// Datasets
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5D.html

struct Dataset : noncopyable
{
    const hid_t id;

    Dataset (InFile & file, const std::string & name)
        : id(H5Dopen(
            file.id,
            name.c_str()
            //, H5P_DEFAULT
            ))
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to open dataset " << name << "\n" << get_error());
    }

    Dataset (
            OutFile & file,
            const std::string & name,
            hid_t type_id,
            Dataspace & dataspace)
        : id(H5Dcreate(
                file.id,
                name.c_str(),
                type_id,
                dataspace.id,
                H5P_DEFAULT
                //, H5P_DEFAULT
                //, H5P_DEFAULT
                ))
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to create dataset " << name << "\n" << get_error());
        POMAGMA_ASSERT_EQ(type(), type_id);
    }

    ~Dataset ()
    {
        POMAGMA_HDF5_OK(H5Dclose(id));
    }

    hid_t type () const { return H5Dget_type(id); }

    template<class T>
    void write_scalar (const T & source)
    {
        POMAGMA_ASSERT_EQ(Dataspace(* this).rank(), 0);

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                 // dataset_id
                Unsigned<T>::id(),  // mem_type_id
                H5S_ALL,            // mem_space_id
                H5S_ALL,            // file_space_id
                H5P_DEFAULT,        // xfer_plist_id
                &source));          // buf
    }

    template<class T>
    void read_scalar (T & destin)
    {
        POMAGMA_ASSERT_EQ(Dataspace(* this).rank(), 0);

        POMAGMA_HDF5_OK(H5Dread(
                id,                 // dataset_id
                Unsigned<T>::id(),  // mem_type_id, 16-bit
                H5S_ALL,            // mem_space_id
                H5S_ALL,            // file_space_id
                H5P_DEFAULT,        // xfer_plist_id
                &destin));          // buf
    }

    template<class T>
    void write_all (const std::vector<T> & source)
    {
        POMAGMA_ASSERT_EQ(Dataspace(* this).volume(), source.size());

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                 // dataset_id
                Unsigned<T>::id(),  // mem_type_id
                H5S_ALL,            // mem_space_id
                H5S_ALL,            // file_space_id
                H5P_DEFAULT,        // xfer_plist_id
                &source[0]));       // buf
    }

    template<class T>
    void read_all (std::vector<T> & destin)
    {
        destin.resize(Dataspace(* this).volume());

        POMAGMA_HDF5_OK(H5Dread(
                id,                 // dataset_id
                Unsigned<T>::id(),  // mem_type_id, 16-bit
                H5S_ALL,            // mem_space_id
                H5S_ALL,            // file_space_id
                H5P_DEFAULT,        // xfer_plist_id
                &destin[0]));       // buf
    }

    void write_all (const DenseSet & source)
    {
        POMAGMA_ASSERT_EQ(type(), Bitfield<Word>::id());
        POMAGMA_ASSERT_EQ(Dataspace(* this).volume(), source.word_dim());

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                     // dataset_id
                Bitfield<Word>::id(),   // mem_type_id
                H5S_ALL,                // mem_space_id
                H5S_ALL,                // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                source.raw_data()));    // buf
    }

    void read_all (DenseSet & destin)
    {
        POMAGMA_ASSERT_EQ(type(), Bitfield<Word>::id());
        POMAGMA_ASSERT_LE(Dataspace(* this).volume(), destin.word_dim());

        POMAGMA_HDF5_OK(H5Dread(
                id,                     // dataset_id
                Bitfield<Word>::id(),   // mem_type_id
                H5S_ALL,                // mem_space_id
                H5S_ALL,                // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                destin.raw_data()));    // buf
    }

    template<class T>
    void write_block (const std::vector<T> & source, size_t offset)
    {
        Dataspace dataspace(* this);
        dataspace.select_block(offset, source.size());

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                 // dataset_id
                Unsigned<T>::id(),  // mem_type_id
                H5S_ALL,            // mem_space_id
                dataspace.id,       // file_space_id
                H5P_DEFAULT,        // xfer_plist_id
                & source[0]));      // buf
    }

    template<class T>
    void read_block (std::vector<T> & destin, size_t offset)
    {
        Dataspace dataspace(* this);
        dataspace.select_block(offset, destin.size());

        POMAGMA_HDF5_OK(H5Dread(
                id,                 // dataset_id
                Unsigned<T>::id(),  // mem_type_id
                H5S_ALL,            // mem_space_id
                dataspace.id,       // file_space_id
                H5P_DEFAULT,        // xfer_plist_id
                & destin[0]));      // buf
    }

    void write_rectangle (
            const std::atomic<Word> * source,
            size_t dim1,
            size_t dim2)
    {
        Dataspace destin_dataspace(*this);
        auto shape = destin_dataspace.shape();
        POMAGMA_ASSERT_EQ(shape.size(), 2);
        POMAGMA_ASSERT_EQ(type(), Bitfield<Word>::id());

        Dataspace source_dataspace(dim1, dim2);

        const hsize_t offset[] = {0, 0};
        const hsize_t count[] = {shape[0], shape[1]};
        source_dataspace.select_hyperslab(offset, count);

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                     // dataset_id
                Bitfield<Word>::id(),   // mem_type_id
                source_dataspace.id,    // mem_space_id
                destin_dataspace.id,    // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                source));               // buf
    }

    void read_rectangle (std::atomic<Word> * destin, size_t dim1, size_t dim2)
    {
        Dataspace destin_dataspace(*this);
        auto shape = destin_dataspace.shape();
        POMAGMA_ASSERT_EQ(shape.size(), 2);
        POMAGMA_ASSERT_EQ(type(), Bitfield<Word>::id());

        Dataspace source_dataspace(dim1, dim2);

        const hsize_t offset[] = {0, 0};
        const hsize_t count[] = {shape[0], shape[1]};
        source_dataspace.select_hyperslab(offset, count);

        POMAGMA_HDF5_OK(H5Dread(
                id,                     // dataset_id
                Bitfield<Word>::id(),   // mem_type_id
                destin_dataspace.id,    // mem_space_id
                source_dataspace.id,    // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                destin));               // buf
    }
};

inline Dataspace::Dataspace (Dataset & dataset)
    : id(H5Dget_space(dataset.id))
{
}

#undef POMAGMA_HDF5_OK

} // namespace hdf5

} // namespace pomagma
