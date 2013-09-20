#pragma once

#include <pomagma/platform/util.hpp>
#include <pomagma/platform/hasher.hpp>
#include <algorithm>

extern "C" {
#include <hdf5.h>
}

namespace pomagma
{

namespace hdf5
{

struct GlobalLock
{
    GlobalLock ();
    ~GlobalLock ();
};

//----------------------------------------------------------------------------
// Errors
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5E.html

inline std::string get_error ()
{
    std::string buffer(4096, '\0');
    FILE * file = fmemopen(&buffer[0], buffer.size(), "w");
    POMAGMA_ASSERT(file, "failed to open error message buffer");
    H5Eprint(file);
    fclose(file);
    return buffer.substr(0, buffer.find('\0'));
}

#define POMAGMA_HDF5_OK(status) POMAGMA_ASSERT((status) >= 0, get_error())

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

inline hid_t unsigned_type_wide_enough_for (size_t max_value)
{
    if (max_value <= std::numeric_limits<uint8_t>::max()) {
        return H5T_NATIVE_UCHAR;
    } else if (max_value <= std::numeric_limits<uint16_t>::max()) {
        return H5T_NATIVE_USHORT;
    } else if (max_value <= std::numeric_limits<uint32_t>::max()) {
        return H5T_NATIVE_UINT;
    } else {
        return H5T_NATIVE_ULONG;
    }
}

inline size_t max_value_of_type (hid_t type)
{
    if (H5Tequal(type, H5T_NATIVE_UCHAR)) {
        return std::numeric_limits<uint8_t>::max();
    } else
    if (H5Tequal(type, H5T_NATIVE_USHORT)) {
        return std::numeric_limits<uint16_t>::max();
    } else
    if (H5Tequal(type, H5T_NATIVE_UINT)) {
        return std::numeric_limits<uint32_t>::max();
    } else
    if (H5Tequal(type, H5T_NATIVE_ULONG)) {
        return std::numeric_limits<uint64_t>::max();
    } else {
        POMAGMA_ERROR("unknown type");
    }
}

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
// Groups
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5G.html

extern "C"
{
static herr_t _group_children_visitor (
        hid_t root_id __attribute__((unused)),
        const char * name,
        const H5L_info_t * object_info __attribute__((unused)),
        void * op_data)
{
    auto * names = static_cast<std::vector<std::string> *>(op_data);
    if (name[0] != '.') { // ignore root group
        //POMAGMA_DEBUG("found child " << name);
        names->push_back(name);
    }
    return 0;
}
}


struct Group : noncopyable
{
    const hid_t id;

private:

    static size_t size_estimate () { return 0; }

    static hid_t open (hid_t loc_id, const std::string & name)
    {
        hid_t id = H5Gopen(loc_id, name.c_str());
        POMAGMA_ASSERT(id >= 0,
                "failed to open group " << name << "\n" << get_error());
        return id;
    }

    static hid_t open_or_create (hid_t loc_id, const std::string & name)
    {
        hid_t id = H5Gopen(loc_id, name.c_str());
        if (id < 0) {
            id = H5Gcreate(loc_id, name.c_str(), size_estimate());
        }
        POMAGMA_ASSERT(id >= 0,
                "failed to create group " << name << "\n" << get_error());
        return id;
    }

public:

    template<class Object>
    Group (Object & object, const std::string & name, bool create = false)
        : id(create ? open_or_create(object.id, name) : open(object.id, name))
    {
    }

    ~Group ()
    {
        POMAGMA_HDF5_OK(H5Gclose(id));
    }

    std::vector<std::string> children ()
    {
        hsize_t idx = 0;
        std::vector<std::string> result;
        POMAGMA_HDF5_OK(H5Literate(
                    id,
                    H5_INDEX_NAME,
                    H5_ITER_NATIVE,
                    & idx,
                    _group_children_visitor,
                    & result));
        return result;
    }

    bool exists (const std::string & name)
    {
        htri_t result = H5Lexists(id, name.c_str(), H5P_DEFAULT);
        POMAGMA_HDF5_OK(result);
        return result;
    }
};

//----------------------------------------------------------------------------
// Dataspaces
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5S.html

class Attribute;
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

    Dataspace (Attribute & attribute);
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
// Attributes
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5A.html

struct Attribute : noncopyable
{
    const hid_t id;

    template<class Object>
    Attribute (Object & object, const std::string & name)
        : id(H5Aopen(
            object.id,
            name.c_str(),
            H5P_DEFAULT
            ))
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to open attribute " << name << "\n" << get_error());
    }

    template<class Object>
    Attribute (
            Object & object,
            const std::string & name,
            hid_t type_id,
            Dataspace & dataspace)
        : id(H5Acreate(
                object.id,
                name.c_str(),
                type_id,
                dataspace.id,
                H5P_DEFAULT
                ))
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to create attribute " << name << "\n" << get_error());
        POMAGMA_ASSERT(H5Tequal(type(), type_id),
                "created attribute with wrong type");
    }

    ~Attribute ()
    {
        POMAGMA_HDF5_OK(H5Aclose(id));
    }

    hid_t type () { return H5Aget_type(id); }
    size_t rank () { return Dataspace(* this).rank(); }
    size_t volume () { return Dataspace(* this).volume(); }

    template<class T>
    void write (const std::vector<T> & source)
    {
        hid_t source_type = Unsigned<T>::id();
        hid_t destin_type = type();
        POMAGMA_ASSERT_EQ(H5Tget_size(source_type), H5Tget_size(destin_type));
        POMAGMA_ASSERT_EQ(volume(), source.size());

        POMAGMA_HDF5_OK(H5Awrite(id, destin_type, & source[0]));
    }

    template<class T>
    void read (std::vector<T> & destin)
    {
        hid_t source_type = type();
        hid_t destin_type = Unsigned<T>::id();
        POMAGMA_ASSERT_EQ(H5Tget_size(source_type), H5Tget_size(destin_type));
        destin.resize(volume());

        POMAGMA_HDF5_OK(H5Aread(id, source_type, & destin[0]));
    }
};

inline Dataspace::Dataspace (Attribute & attribute)
    : id(H5Aget_space(attribute.id))
{
}

//----------------------------------------------------------------------------
// Datasets
// http://www.hdfgroup.org/HDF5/doc/RM/RM_H5D.html

struct Dataset : noncopyable
{
    const hid_t id;

    template<class Object>
    Dataset (Object & object, const std::string & name)
        : id(H5Dopen(
            object.id,
            name.c_str()
            //, H5P_DEFAULT
            ))
    {
        POMAGMA_ASSERT(id >= 0,
                "failed to open dataset " << name << "\n" << get_error());
    }

    template<class Object>
    Dataset (
            Object & object,
            const std::string & name,
            hid_t type_id,
            Dataspace & dataspace)
        : id(H5Dcreate(
                object.id,
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
        POMAGMA_ASSERT(H5Tequal(type(), type_id),
                "created dataset with wrong type");
    }

    ~Dataset ()
    {
        POMAGMA_HDF5_OK(H5Dclose(id));
    }

    hid_t type () { return H5Dget_type(id); }
    size_t rank () { return Dataspace(* this).rank(); }
    size_t volume () { return Dataspace(* this).volume(); }

    template<class T>
    void write_scalar (const T & source)
    {
        hid_t source_type = Unsigned<T>::id();
        hid_t destin_type = type();
        if (H5Tget_size(source_type) > H5Tget_size(destin_type)) {
            POMAGMA_ASSERT_LE(source, max_value_of_type(destin_type));
        }

        POMAGMA_ASSERT_EQ(rank(), 0);

        POMAGMA_HDF5_OK(H5Dwrite(
                id,             // dataset_id
                source_type,    // mem_type_id
                H5S_ALL,        // mem_space_id
                H5S_ALL,        // file_space_id
                H5P_DEFAULT,    // xfer_plist_id
                & source));     // buf
    }

    template<class T>
    void read_scalar (T & destin)
    {
        hid_t source_type = type();
        hid_t destin_type = Unsigned<T>::id();
        POMAGMA_ASSERT_LE(H5Tget_size(source_type), H5Tget_size(destin_type));

        POMAGMA_ASSERT_EQ(rank(), 0);

        POMAGMA_HDF5_OK(H5Dread(
                id,             // dataset_id
                destin_type,    // mem_type_id
                H5S_ALL,        // mem_space_id
                H5S_ALL,        // file_space_id
                H5P_DEFAULT,    // xfer_plist_id
                & destin));     // buf
    }

    template<class T>
    void write_all (const std::vector<T> & source)
    {
        hid_t source_type = Unsigned<T>::id();
        hid_t destin_type = type();
        if (H5Tget_size(source_type) > H5Tget_size(destin_type)) {
            size_t max_value = * std::max_element(source.begin(), source.end());
            POMAGMA_ASSERT_LE(max_value, max_value_of_type(destin_type));
        }

        POMAGMA_ASSERT_EQ(volume(), source.size());

        POMAGMA_HDF5_OK(H5Dwrite(
                id,             // dataset_id
                source_type,    // mem_type_id
                H5S_ALL,        // mem_space_id
                H5S_ALL,        // file_space_id
                H5P_DEFAULT,    // xfer_plist_id
                & source[0]));  // buf
    }

    template<class T>
    void read_all (std::vector<T> & destin)
    {
        hid_t source_type = type();
        hid_t destin_type = Unsigned<T>::id();
        POMAGMA_ASSERT_LE(H5Tget_size(source_type), H5Tget_size(destin_type));

        destin.resize(volume());

        POMAGMA_HDF5_OK(H5Dread(
                id,             // dataset_id
                destin_type,    // mem_type_id
                H5S_ALL,        // mem_space_id
                H5S_ALL,        // file_space_id
                H5P_DEFAULT,    // xfer_plist_id
                & destin[0]));  // buf
    }

    template<class DenseSet>
    void write_set (const DenseSet & source)
    {
        hid_t source_type = Bitfield<Word>::id();
        hid_t destin_type = type();
        POMAGMA_ASSERT(H5Tequal(source_type, destin_type), "datatype mismatch");

        POMAGMA_ASSERT_EQ(volume(), source.word_dim());

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                     // dataset_id
                source_type,            // mem_type_id
                H5S_ALL,                // mem_space_id
                H5S_ALL,                // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                source.raw_data()));    // buf
    }

    template<class DenseSet>
    void read_set (DenseSet & destin)
    {
        hid_t source_type = type();
        hid_t destin_type = Bitfield<Word>::id();
        POMAGMA_ASSERT(H5Tequal(source_type, destin_type), "datatype mismatch");

        POMAGMA_ASSERT_LE(volume(), destin.word_dim());

        POMAGMA_HDF5_OK(H5Dread(
                id,                     // dataset_id
                destin_type,            // mem_type_id
                H5S_ALL,                // mem_space_id
                H5S_ALL,                // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                destin.raw_data()));    // buf
    }

    template<class T>
    void write_block (const std::vector<T> & source, size_t offset)
    {
        hid_t source_type = Unsigned<T>::id();
        hid_t destin_type = type();
        if (H5Tget_size(source_type) > H5Tget_size(destin_type)) {
            size_t max_value = * std::max_element(source.begin(), source.end());
            POMAGMA_ASSERT_LE(max_value, max_value_of_type(destin_type));
        }

        Dataspace source_dataspace(source.size());
        Dataspace destin_dataspace(* this);
        destin_dataspace.select_block(offset, source.size());

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                     // dataset_id
                source_type,            // mem_type_id
                source_dataspace.id,    // mem_space_id
                destin_dataspace.id,    // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                & source[0]));          // buf
    }

    template<class T>
    void read_block (std::vector<T> & destin, size_t offset)
    {
        hid_t source_type = type();
        hid_t destin_type = Unsigned<T>::id();
        POMAGMA_ASSERT_LE(H5Tget_size(source_type), H5Tget_size(destin_type));

        Dataspace destin_dataspace(destin.size());
        Dataspace source_dataspace(* this);
        source_dataspace.select_block(offset, destin.size());

        POMAGMA_HDF5_OK(H5Dread(
                id,                     // dataset_id
                destin_type,            // mem_type_id
                destin_dataspace.id,    // mem_space_id
                source_dataspace.id,    // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                & destin[0]));          // buf
    }

    template<class atomic_Word>
    void write_rectangle (
            const atomic_Word * source,
            size_t source_dim1,
            size_t source_dim2)
    {
        static_assert(sizeof(atomic_Word) == sizeof(Word), "bad word type");
        hid_t source_type = Bitfield<Word>::id();
        hid_t destin_type = type();
        POMAGMA_ASSERT(H5Tequal(source_type, destin_type), "datatype mismatch");

        Dataspace destin_dataspace(* this);
        auto shape = destin_dataspace.shape();
        POMAGMA_ASSERT_EQ(shape.size(), 2);

        Dataspace source_dataspace(source_dim1, source_dim2);
        const hsize_t offset[] = {0, 0};
        const hsize_t count[] = {shape[0], shape[1]};
        source_dataspace.select_hyperslab(offset, count);

        POMAGMA_HDF5_OK(H5Dwrite(
                id,                     // dataset_id
                source_type,            // mem_type_id
                source_dataspace.id,    // mem_space_id
                destin_dataspace.id,    // file_space_id
                H5P_DEFAULT,            // xfer_plist_id
                source));               // buf
    }

    template<class atomic_Word>
    void read_rectangle (
            atomic_Word * destin,
            size_t destin_dim1,
            size_t destin_dim2)
    {
        static_assert(sizeof(atomic_Word) == sizeof(Word), "bad word type");
        hid_t source_type = type();
        hid_t destin_type = Bitfield<Word>::id();
        POMAGMA_ASSERT(H5Tequal(source_type, destin_type), "datatype mismatch");

        Dataspace source_dataspace(* this);
        auto shape = source_dataspace.shape();
        POMAGMA_ASSERT_EQ(shape.size(), 2);
        POMAGMA_ASSERT_LE(shape[0], destin_dim1);
        POMAGMA_ASSERT_LE(shape[1], destin_dim2);

        Dataspace destin_dataspace(destin_dim1, destin_dim2);
        const hsize_t offset[] = {0, 0};
        const hsize_t count[] = {shape[0], shape[1]};
        destin_dataspace.select_hyperslab(offset, count);

        POMAGMA_HDF5_OK(H5Dread(
                id,                     // dataset_id
                destin_type,            // mem_type_id
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

//----------------------------------------------------------------------------
// Hashing

template<class Object>
inline bool has_hash (Object & object)
{
    herr_t exists = H5Aexists(object.id, "hash");
    POMAGMA_HDF5_OK(exists);
    return exists;
}

template<class Object>
inline void dump_hash (const Object & object, const Hasher::Digest & digest)
{
    Dataspace dataspace(digest.size());
    auto type_id = Unsigned<Hasher::Digest::value_type>::id();
    Attribute attribute(object, "hash", type_id, dataspace);
    attribute.write(digest);
}

template<class Object>
inline Hasher::Digest load_hash (const Object & object)
{
    Attribute attribute(object, "hash");
    Hasher::Digest digest;
    attribute.read(digest);
    return digest;
}

namespace
{
struct OpaqueObject
{
    const hid_t id;

    OpaqueObject (hid_t loc_id, haddr_t addr)
        : id(H5Oopen_by_addr(loc_id, addr))
    {
        POMAGMA_ASSERT(id >= 0, "failed to create raw object");
    }

    ~OpaqueObject ()
    {
        H5Oclose(id);
    }
};
} // anonymous namespace

extern "C"
{
static herr_t _tree_hash_visitor (
        hid_t root_id,
        const char * name,
        const H5O_info_t * object_info,
        void * op_data)
{
    if (name[0] != '.') { // ignore root group
        OpaqueObject object(root_id, object_info->addr);
        if (has_hash(object)) {
            POMAGMA_DEBUG("loading hash at " << name);
            auto & dict = * static_cast<Hasher::Dict *>(op_data);
            dict[name] = load_hash(object);
        }
    }
    return 0;
}
}

template<class Object>
inline Hasher::Digest get_tree_hash (const Object & object)
{
    Hasher::Dict dict;
    POMAGMA_HDF5_OK(H5Ovisit(
                object.id,
                H5_INDEX_NAME,
                H5_ITER_NATIVE,
                _tree_hash_visitor,
                & dict));
    POMAGMA_ASSERT(not dict.empty(), "no hashes were found in object tree");
    return Hasher::digest(dict);
}

#undef POMAGMA_HDF5_OK

} // namespace hdf5

} // namespace pomagma
