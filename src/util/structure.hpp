#pragma once

// Assumes the following are defined:
// DenseSet
// Carrier
// BinaryRelation
// NullaryFunction
// InjectiveFunction
// BinaryFunction
// SymmetricFunction
#include <pomagma/util/hdf5.hpp>
#include <array>

namespace pomagma
{

//----------------------------------------------------------------------------
// Interface

inline void clear (
        Signature & signature);

inline void clear_data (
        Signature & signature);

inline void dump (
        Signature & signature,
        hdf5::OutFile & file);

inline void load (
        Signature & signature,
        hdf5::InFile & file,
        size_t extra_item_dim = 0);

inline void load_data (
        Signature & signature,
        hdf5::InFile & file);

//----------------------------------------------------------------------------
// Clearing

inline void clear (
        Signature & signature)
{
    POMAGMA_INFO("Clearing signature");

    if (signature.carrier()) {
        for (auto i : signature.binary_relations()) { delete i.second; }
        for (auto i : signature.nullary_functions()) { delete i.second; }
        for (auto i : signature.injective_functions()) { delete i.second; }
        for (auto i : signature.binary_functions()) { delete i.second; }
        for (auto i : signature.symmetric_functions()) { delete i.second; }
        delete signature.carrier();
    }
    signature.clear();
}

inline void clear_data (
        Signature & signature)
{
    POMAGMA_INFO("Clearing signature data");
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    if (signature.carrier()->item_count()) {
        for (auto i : signature.binary_relations()) { i.second->clear(); }
        for (auto i : signature.nullary_functions()) { i.second->clear(); }
        for (auto i : signature.injective_functions()) { i.second->clear(); }
        for (auto i : signature.binary_functions()) { i.second->clear(); }
        for (auto i : signature.symmetric_functions()) { i.second->clear(); }
        signature.carrier()->clear();
    }
}

//----------------------------------------------------------------------------
// Hashing

namespace detail
{

inline Hasher::Digest get_hash (const Carrier & carrier)
{
    Hasher hasher;
    for (auto i = carrier.iter(); i.ok(); i.next()) {
        uint32_t data = * i;
        hasher.add(data);
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash (
        const Carrier & carrier,
        const BinaryRelation & rel)
{
    Hasher hasher;
    std::array<uint32_t, 2> tuple;
    for (auto lhs = carrier.iter(); lhs.ok(); lhs.next()) {
        tuple[0] = * lhs;
        for (auto rhs = rel.iter_lhs(* lhs); rhs.ok(); rhs.next()) {
            tuple[1] = * rhs;
            hasher.add(tuple);
        }
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash (const NullaryFunction & fun)
{
    std::array<uint32_t, 1> tuple;
    tuple[0] = fun.find();
    return Hasher::digest(tuple);
}

inline Hasher::Digest get_hash (const InjectiveFunction & fun)
{
    Hasher hasher;
    std::array<uint32_t, 2> tuple;
    for (auto key = fun.iter(); key.ok(); key.next()) {
        tuple[0] = * key;
        tuple[1] = fun.find(* key);
        hasher.add(tuple);
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash (
        const Carrier & carrier,
        const BinaryFunction & fun)
{
    Hasher hasher;
    std::array<uint32_t, 3> tuple;
    for (auto lhs = carrier.iter(); lhs.ok(); lhs.next()) {
        tuple[0] = * lhs;
        for (auto rhs = fun.iter_lhs(* lhs); rhs.ok(); rhs.next()) {
            tuple[1] = * rhs;
            tuple[2] = fun.find(* lhs, * rhs);
            hasher.add(tuple);
        }
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash (
        const Carrier & carrier,
        const SymmetricFunction & fun)
{
    Hasher hasher;
    std::array<uint32_t, 3> tuple;
    for (auto lhs = carrier.iter(); lhs.ok(); lhs.next()) {
        tuple[0] = * lhs;
        for (auto rhs = fun.iter_lhs(* lhs); rhs.ok(); rhs.next()) {
            if (* rhs > * lhs) { break; }
            tuple[1] = * rhs;
            tuple[2] = fun.find(* lhs, * rhs);
            hasher.add(tuple);
        }
    }
    return hasher.finish();
}

} // namespace detail

//----------------------------------------------------------------------------
// Dumping

namespace detail
{

inline void dump (
        const Carrier & carrier,
        hdf5::OutFile & file)
{
    POMAGMA_INFO("dumping carrier");

    auto ob_type = hdf5::Bitfield<Word>::id();

    const DenseSet & support = carrier.support();
    hdf5::Dataspace dataspace(support.word_dim());

    hdf5::Group group(file, "carrier", true);
    hdf5::Dataset dataset(group, "support", ob_type, dataspace);

    dataset.write_set(support);

    auto digest = get_hash(carrier);
    hdf5::dump_hash(group, digest);
}

inline void dump (
        const Carrier & carrier,
        const BinaryRelation & rel,
        hdf5::OutFile & file,
        const std::string & name)
{
    POMAGMA_INFO("dumping binary/relations/" << name);

    auto word_type = hdf5::Bitfield<Word>::id();

    const DenseSet & support = carrier.support();
    const size_t item_dim = support.item_dim();
    const size_t word_dim = support.word_dim();
    hdf5::Dataspace dataspace(1 + item_dim, word_dim);

    hdf5::Group group1(file, "relations", true);
    hdf5::Group group2(group1, "binary", true);
    hdf5::Dataset dataset(group2, name, word_type, dataspace);

    size_t dim1 = 1 + rel.item_dim();
    size_t dim2 = rel.round_word_dim();
    const auto * source = rel.raw_data();
    dataset.write_rectangle(source, dim1, dim2);

    auto digest = get_hash(carrier, rel);
    hdf5::dump_hash(dataset, digest);
}

inline void dump (
        const Carrier & carrier,
        const NullaryFunction & fun,
        hdf5::OutFile & file,
        const std::string & name)
{
    POMAGMA_INFO("dumping functions/nullary/" << name);

    auto ob_type = hdf5::Unsigned<Ob>::id();

    hdf5::Dataspace dataspace;

    hdf5::Group group1(file, "functions", true);
    hdf5::Group group2(group1, "nullary", true);
    hdf5::Group group3(group2, name, true);
    hdf5::Dataset dataset(group3, "value", ob_type, dataspace);

    Ob data = fun.find();
    POMAGMA_ASSERT_LE(data, carrier.item_dim());
    dataset.write_scalar(data);

    auto digest = get_hash(fun);
    hdf5::dump_hash(group3, digest);
}

inline void dump (
        const Carrier & carrier,
        const InjectiveFunction & fun,
        hdf5::OutFile & file,
        const std::string & name)
{
    // format:
    // dense array with null entries

    POMAGMA_INFO("dumping functions/injective/" << name);

    auto ob_type = hdf5::Unsigned<Ob>::id();

    const size_t item_dim = carrier.item_dim();
    hdf5::Dataspace dataspace(1 + item_dim);

    hdf5::Group group1(file, "functions", true);
    hdf5::Group group2(group1, "injective", true);
    hdf5::Group group3(group2, name, true);
    hdf5::Dataset dataset(group3, "value", ob_type, dataspace);

    std::vector<Ob> data(1 + item_dim, 0);
    for (auto key = fun.iter(); key.ok(); key.next()) {
        data[* key] = fun.raw_find(* key);
    }
    dataset.write_all(data);

    auto digest = get_hash(fun);
    hdf5::dump_hash(group3, digest);
}

template<class Function>
inline void dump (
        const Carrier & carrier,
        const Function & fun,
        hdf5::OutFile & file,
        const std::string & arity,
        const std::string & name)
{
    // format:
    // compressed sparse row (CSR) matrix

    POMAGMA_INFO("dumping functions/" << arity << "/" << name);

    typedef uint_<2 * sizeof(Ob)>::t ptr_t;
    auto ptr_type = hdf5::Unsigned<ptr_t>::id();
    auto ob_type = hdf5::Unsigned<Ob>::id();

    const size_t item_dim = carrier.item_dim();
    hdf5::Dataspace ptr_dataspace(1 + item_dim);
    size_t pair_count = fun.count_pairs();
    POMAGMA_DEBUG("dumping " << pair_count << " lhs,rhs pairs");
    hdf5::Dataspace ob_dataspace(pair_count);

    hdf5::Group group1(file, "functions", true);
    hdf5::Group group2(group1, arity, true);
    hdf5::Group group3(group2, name, true);
    hdf5::Dataset lhs_ptr_dataset(group3, "lhs_ptr", ptr_type, ptr_dataspace);
    hdf5::Dataset rhs_dataset(group3, "rhs", ob_type, ob_dataspace);
    hdf5::Dataset value_dataset(group3, "value", ob_type, ob_dataspace);

    std::vector<ptr_t> lhs_ptr_data(1 + item_dim);
    std::vector<Ob> rhs_data(item_dim);
    std::vector<Ob> value_data(item_dim);
    ptr_t pos = 0;
    lhs_ptr_data[0] = pos;
    for (Ob lhs = 1; lhs <= item_dim; ++lhs) {
        lhs_ptr_data[lhs] = pos;
        if (carrier.contains(lhs)) {
            rhs_data.clear();
            value_data.clear();
            for (auto rhs = fun.iter_lhs(lhs); rhs.ok(); rhs.next()) {
                if (Function::is_symmetric() and * rhs > lhs) { break; }
                rhs_data.push_back(* rhs);
                value_data.push_back(fun.raw_find(lhs, * rhs));
            }
            if (size_t count = rhs_data.size()) {
                ptr_t nextpos = pos + count;
                POMAGMA_ASSERT_LE(nextpos, pair_count);
                rhs_dataset.write_block(rhs_data, pos);
                value_dataset.write_block(value_data, pos);
                pos = nextpos;
            }
        }
    }
    POMAGMA_ASSERT_EQ(pos, pair_count);
    lhs_ptr_dataset.write_all(lhs_ptr_data);

    auto digest = get_hash(carrier, fun);
    hdf5::dump_hash(group3, digest);
}

} // namespace detail

inline void dump (
        Signature & signature,
        hdf5::OutFile & file)
{
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    const Carrier & carrier = * signature.carrier();

    // TODO parallelize
    detail::dump(carrier, file);
    for (const auto & pair : signature.binary_relations()) {
        detail::dump(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.nullary_functions()) {
        detail::dump(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.injective_functions()) {
        detail::dump(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.binary_functions()) {
        detail::dump(carrier, * pair.second, file, "binary", pair.first);
    }
    for (const auto & pair : signature.symmetric_functions()) {
        detail::dump(carrier, * pair.second, file, "symmetric", pair.first);
    }

    auto digest = hdf5::get_tree_hash(file);
    hdf5::dump_hash(file, digest);
}

//----------------------------------------------------------------------------
// Loading

// adapted from
// http://www.hdfgroup.org/HDF5/Tutor/crtfile.html

namespace detail
{

inline void load_signature (
        Signature & signature,
        hdf5::InFile & file,
        size_t extra_item_dim)
{
    POMAGMA_INFO("Loading signature");

    clear(signature);
    // there must at least be a carrier and nullary functions
    {
        hdf5::Group group(file, "carrier");
        hdf5::Dataset dataset(group, "support");
        hdf5::Dataspace dataspace(dataset);
        POMAGMA_ASSERT_EQ(dataspace.rank(), 1);
        size_t source_item_dim = dataspace.volume() * BITS_PER_WORD - 1;
        size_t destin_item_dim = source_item_dim + extra_item_dim;
        signature.declare(* new Carrier(destin_item_dim));
    }
    Carrier & carrier = * signature.carrier();
    {
        hdf5::Group group1(file, "relations");
        if (group1.exists("binary")) {
            hdf5::Group group2(group1, "binary");
            for (auto name : group2.children()) {
                signature.declare(name, * new BinaryRelation(carrier));
            }
        }
    }
    {
        hdf5::Group group1(file, "functions");
        {
            hdf5::Group group2(group1, "nullary");
            for (auto name : group2.children()) {
                signature.declare(name, * new NullaryFunction(carrier));
            }
        }
        if (group1.exists("injective")) {
            hdf5::Group group2(group1, "injective");
            for (auto name : group2.children()) {
                signature.declare(name, * new InjectiveFunction(carrier));
            }
        }
        if (group1.exists("binary")) {
            hdf5::Group group2(group1, "binary");
            for (auto name : group2.children()) {
                signature.declare(name, * new BinaryFunction(carrier));
            }
        }
        if (group1.exists("symmetric")) {
            hdf5::Group group2(group1, "symmetric");
            for (auto name : group2.children()) {
                signature.declare(name, * new SymmetricFunction(carrier));
            }
        }
    }
}

// check that all structure in file is already contained in signature
inline void check_signature (
        Signature & signature,
        hdf5::InFile & file)
{
    POMAGMA_INFO("Checking signature");

    // there must at least be a carrier and nullary functions
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    const Carrier & carrier = * signature.carrier();
    {
        hdf5::Group group(file, "carrier");
        hdf5::Dataset dataset(group, "support");
        hdf5::Dataspace dataspace(dataset);
        POMAGMA_ASSERT_EQ(dataspace.rank(), 1);
        size_t source_item_dim = dataspace.volume() * BITS_PER_WORD - 1;
        size_t destin_item_dim = carrier.item_dim();
        POMAGMA_ASSERT_LE(source_item_dim, destin_item_dim);
    }
    {
        hdf5::Group group1(file, "relations");
        if (group1.exists("binary")) {
            hdf5::Group group2(group1, "binary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.binary_relations(name),
                        "file has unknown binary relation " << name);
            }
        }
    }
    {
        hdf5::Group group1(file, "functions");
        {
            hdf5::Group group2(group1, "nullary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.nullary_functions(name),
                        "file has unknown nullary function " << name);
            }
        }
        if (group1.exists("injective")) {
            hdf5::Group group2(group1, "injective");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.injective_functions(name),
                        "file has unknown injective function " << name);
            }
        }
        if (group1.exists("binary")) {
            hdf5::Group group2(group1, "binary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.binary_functions(name),
                        "file has unknown binary function " << name);
            }
        }
        if (group1.exists("symmetric")) {
            hdf5::Group group2(group1, "symmetric");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.symmetric_functions(name),
                        "file has unknown symmetric function " << name);
            }
        }
    }
}

inline void load_data (
        Carrier & carrier,
        hdf5::InFile & file)
{
    POMAGMA_INFO("loading carrier");

    hdf5::Group group(file, "carrier");
    hdf5::Dataset dataset(group, "support");

    DenseSet support(carrier.item_dim());
    dataset.read_set(support);
    for (auto i = support.iter(); i.ok(); i.next()) {
        carrier.raw_insert(* i);
    }
    carrier.update();
    POMAGMA_ASSERT_EQ(carrier.rep_count(), carrier.item_count());

    auto digest = get_hash(carrier);
    POMAGMA_ASSERT(digest == hdf5::load_hash(group), "carrier is corrupt");
}

inline void load_data (
        const Carrier & carrier,
        BinaryRelation & rel,
        hdf5::InFile & file,
        const std::string & name)
{
    POMAGMA_INFO("loading binary relation " << name);

    size_t dim1 = 1 + rel.item_dim();
    size_t dim2 = rel.round_word_dim();
    auto * destin = rel.raw_data();

    hdf5::Group group1(file, "relations");
    hdf5::Group group2(group1, "binary");
    hdf5::Dataset dataset(group2, name);

    dataset.read_rectangle(destin, dim1, dim2);
    rel.update();

    auto digest = get_hash(carrier, rel);
    POMAGMA_ASSERT(digest == hdf5::load_hash(dataset),
            "binary relation " << name << " is corrupt");
}

inline void load_data (
        const Carrier & carrier,
        NullaryFunction & fun,
        hdf5::InFile & file,
        const std::string & name)
{
    POMAGMA_INFO("loading nullary function " << name);

    const size_t item_dim = carrier.item_dim();

    hdf5::Group group1(file, "functions");
    hdf5::Group group2(group1, "nullary");
    hdf5::Group group3(group2, name);
    hdf5::Dataset dataset(group3, "value");

    Ob data;
    dataset.read_scalar(data);
    POMAGMA_ASSERT_LE(data, item_dim);
    fun.raw_insert(data);

    auto digest = get_hash(fun);
    POMAGMA_ASSERT(digest == hdf5::load_hash(group3),
            "nullary function " << name << " is corrupt");
}

inline void load_data (
        const Carrier & carrier,
        InjectiveFunction & fun,
        hdf5::InFile & file,
        const std::string & name)
{
    POMAGMA_INFO("loading injective function " << name);

    const size_t item_dim = carrier.item_dim();

    hdf5::Group group1(file, "functions");
    hdf5::Group group2(group1, "injective");
    hdf5::Group group3(group2, name);
    hdf5::Dataset dataset(group3, "value");

    std::vector<Ob> data(1 + item_dim);
    dataset.read_all(data);
    for (Ob key = 1; key <= item_dim; ++key) {
        if (Ob value = data[key]) {
            fun.raw_insert(key, value);
        }
    }

    auto digest = get_hash(fun);
    POMAGMA_ASSERT(digest == hdf5::load_hash(dataset),
            "injective function " << name << " is corrupt");
}

template<class Function>
inline void load_data (
        const Carrier & carrier,
        Function & fun,
        hdf5::InFile & file,
        const std::string & arity,
        const std::string & name)
{
    POMAGMA_INFO("loading " << arity << " function " << name);

    const size_t item_dim = carrier.item_dim();
    typedef uint_<2 * sizeof(Ob)>::t ptr_t;

    hdf5::Group group1(file, "functions");
    hdf5::Group group2(group1, arity);
    hdf5::Group group3(group2, name);
    hdf5::Dataset lhs_ptr_dataset(group3,"lhs_ptr");
    hdf5::Dataset rhs_dataset(group3, "rhs");
    hdf5::Dataset value_dataset(group3, "value");
    hdf5::Dataspace lhs_ptr_dataspace(lhs_ptr_dataset);
    hdf5::Dataspace rhs_dataspace(rhs_dataset);
    hdf5::Dataspace value_dataspace(value_dataset);

    auto lhs_ptr_shape = lhs_ptr_dataspace.shape();
    POMAGMA_ASSERT_EQ(lhs_ptr_shape.size(), 1);
    POMAGMA_ASSERT_LE(lhs_ptr_shape[0], 1 + item_dim);
    POMAGMA_ASSERT_EQ(rhs_dataspace.shape(), value_dataspace.shape());

    std::vector<ptr_t> lhs_ptr_data(1 + item_dim);
    std::vector<Ob> rhs_data(item_dim);
    std::vector<Ob> value_data(item_dim);

    lhs_ptr_dataset.read_all(lhs_ptr_data);
    lhs_ptr_data.push_back(rhs_dataspace.volume());
    for (Ob lhs = 1; lhs < lhs_ptr_data.size() - 1; ++lhs) {
        size_t begin = lhs_ptr_data[lhs];
        size_t end = lhs_ptr_data[lhs + 1];
        POMAGMA_ASSERT_LE(begin, end);
        if (size_t count = end - begin) {
            POMAGMA_ASSERT_LE(count, item_dim);

            rhs_data.resize(count); // XXX FIXME segfault here in free.copy
            rhs_dataset.read_block(rhs_data, begin);

            value_data.resize(count);
            value_dataset.read_block(value_data, begin);

            for (size_t i = 0; i < count; ++i) {
                fun.raw_insert(lhs, rhs_data[i], value_data[i]);
            }
        }
    }

    auto digest = get_hash(carrier, fun);
    POMAGMA_ASSERT(digest == hdf5::load_hash(group3),
            arity << " function " << name << " is corrupt");
}

inline void load_data (
        Signature & signature,
        hdf5::InFile & file)
{
    POMAGMA_INFO("Loading structure data");

    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    Carrier & carrier = * signature.carrier();

    // TODO parallelize
    load_data(carrier, file);
    for (const auto & pair : signature.binary_relations()) {
        load_data(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.nullary_functions()) {
        load_data(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.injective_functions()) {
        load_data(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.binary_functions()) {
        load_data(carrier, * pair.second, file, "binary", pair.first);
    }
    for (const auto & pair : signature.symmetric_functions()) {
        load_data(carrier, * pair.second, file, "symmetric", pair.first);
    }
}

} // namespace detail

inline void load (
        Signature & signature,
        hdf5::InFile & file,
        size_t extra_item_dim)
{
    auto digest = hdf5::get_tree_hash(file);
    POMAGMA_ASSERT(digest == hdf5::load_hash(file), "file is corrupt");

    detail::load_signature(signature, file, extra_item_dim);
    detail::load_data(signature, file);
}

inline void load_data (
        Signature & signature,
        hdf5::InFile & file)
{
    auto digest = hdf5::get_tree_hash(file);
    POMAGMA_ASSERT(digest == hdf5::load_hash(file), "file is corrupt");

    detail::check_signature(signature, file);
    detail::load_data(signature, file);
}

} // namespace pomagma
