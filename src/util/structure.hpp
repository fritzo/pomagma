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
// Hashing

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

//----------------------------------------------------------------------------
// Dumping

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

inline void dump (
        Signature & signature,
        hdf5::OutFile & file)
{
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    const Carrier & carrier = * signature.carrier();

    // TODO parallelize
    dump(carrier, file);
    for (const auto & pair : signature.binary_relations()) {
        dump(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.nullary_functions()) {
        dump(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.injective_functions()) {
        dump(carrier, * pair.second, file, pair.first);
    }
    for (const auto & pair : signature.binary_functions()) {
        dump(carrier, * pair.second, file, "binary", pair.first);
    }
    for (const auto & pair : signature.symmetric_functions()) {
        dump(carrier, * pair.second, file, "symmetric", pair.first);
    }

    auto digest = hdf5::get_tree_hash(file);
    hdf5::dump_hash(file, digest);
}

} // namespace pomagma
