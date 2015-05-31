#pragma once

// Assumes the following are defined:
// DenseSet
// Ob
// Carrier
// UnaryRelation
// BinaryRelation
// NullaryFunction
// InjectiveFunction
// BinaryFunction
// SymmetricFunction
#include <pomagma/platform/blobstore.hpp>
#include <pomagma/platform/hdf5.hpp>
#include <pomagma/platform/structure.pb.h>
#include <pomagma/protobuf/stream.hpp>
#include <array>
#include <thread>
#include <algorithm>
#include <sys/stat.h>  // for chmod

namespace pomagma
{

//----------------------------------------------------------------------------
// Interface

void validate_consistent (Signature & signature);
void validate (Signature & signature);
void clear (Signature & signature);
void clear_data (Signature & signature);
void log_stats (Signature & signature);

void dump (Signature & signature, const std::string & filename);

void load (
        Signature & signature,
        const std::string & filename,
        size_t extra_item_dim = 0);

void load_data (
        Signature & signature,
        const std::string & filename);


//----------------------------------------------------------------------------
// Validation

void validate_consistent (Signature & signature)
{
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    for (auto i : signature.unary_relations()) {
        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            auto * pos = i.second;
            if (auto * neg = signature.unary_relation(negated)) {
                pos->validate_disjoint(*neg);
            }
        }
    }
    for (auto i : signature.binary_relations()) {
        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            auto * pos = i.second;
            if (auto * neg = signature.binary_relation(negated)) {
                pos->validate_disjoint(*neg);
            }
        }
    }
}

void validate (Signature & signature)
{
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    std::vector<std::thread> threads;

    // do expensive tasks in parallel
    for (auto i : signature.binary_relations()) {
        auto * pos = i.second;
        threads.push_back(std::thread([pos](){ pos->validate(); }));

        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            if (auto * neg = signature.binary_relation(negated)) {
                threads.push_back(std::thread([pos, neg](){
                    pos->validate_disjoint(*neg);
                }));
            }
        }
    }
    for (auto i : signature.binary_functions()) {
        auto * fun = i.second;
        threads.push_back(std::thread([fun](){ fun->validate(); }));
    }
    for (auto i : signature.symmetric_functions()) {
        auto * fun = i.second;
        threads.push_back(std::thread([fun](){ fun->validate(); }));
    }

    // do everything else in this thread
    for (auto i : signature.unary_relations()) {
        auto * pos = i.second;
        pos->validate();

        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            if (auto * neg = signature.unary_relation(negated)) {
                pos->validate_disjoint(*neg);
            }
        }
    }
    for (auto i : signature.injective_functions()) {
        auto * fun = i.second;
        fun->validate();
    }
    for (auto i : signature.nullary_functions()) {
        auto * fun = i.second;
        fun->validate();
    }
    signature.carrier()->validate();

    for (auto & thread : threads) { thread.join(); }
}

//----------------------------------------------------------------------------
// Clearing

void clear (Signature & signature)
{
    POMAGMA_INFO("Clearing signature");

    if (signature.carrier()) {
        for (auto i : signature.unary_relations()) { delete i.second; }
        for (auto i : signature.binary_relations()) { delete i.second; }
        for (auto i : signature.nullary_functions()) { delete i.second; }
        for (auto i : signature.injective_functions()) { delete i.second; }
        for (auto i : signature.binary_functions()) { delete i.second; }
        for (auto i : signature.symmetric_functions()) { delete i.second; }
        delete signature.carrier();
    }
    signature.clear();
}

void clear_data (Signature & signature)
{
    POMAGMA_INFO("Clearing signature data");
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    if (signature.carrier()->item_count()) {
        for (auto i : signature.unary_relations()) { i.second->clear(); }
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

inline Hasher::Digest get_hash (const UnaryRelation & rel)
{
    Hasher hasher;
    for (auto i = rel.iter(); i.ok(); i.next()) {
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

inline void assert_contiguous (const Carrier & carrier)
{
    size_t max_item = 0;
    size_t item_count = 0;
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        max_item = * iter;
        ++item_count;
    }
    POMAGMA_ASSERT(max_item == item_count,
            "dumping requires contiguous carrier; try compacting first");
}

inline void dump (
        const Carrier & carrier,
        hdf5::OutFile & file)
{
    POMAGMA_DEBUG("dumping carrier");

    size_t max_ob = carrier.item_count(); // carrier is contiguous
    auto ob_type = hdf5::unsigned_type_wide_enough_for(max_ob);

    hdf5::Dataspace dataspace(carrier.item_count());

    hdf5::Group group(file, "carrier", true);
    hdf5::Dataset dataset(group, "points", ob_type, dataspace);

    std::vector<Ob> data;
    data.reserve(carrier.item_count());
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        data.push_back(* iter);
    }
    dataset.write_all(data);

    auto digest = get_hash(carrier);
    hdf5::dump_hash(group, digest);
}

inline void dump (
        const Carrier & carrier,
        const UnaryRelation & rel,
        hdf5::OutFile & file,
        const std::string & name)
{
    POMAGMA_DEBUG("dumping unary/relations/" << name);

    size_t max_ob = carrier.item_count(); // carrier is contiguous
    auto ob_type = hdf5::unsigned_type_wide_enough_for(max_ob);

    size_t item_count = rel.count_items();
    hdf5::Dataspace dataspace(item_count);

    hdf5::Group group1(file, "relations", true);
    hdf5::Group group2(group1, "unary", true);
    hdf5::Dataset dataset(group2, name, ob_type, dataspace);

    std::vector<Ob> data;
    data.reserve(item_count);
    for (auto iter = rel.iter(); iter.ok(); iter.next()) {
        data.push_back(* iter);
    }
    dataset.write_all(data);

    auto digest = get_hash(rel);
    hdf5::dump_hash(dataset, digest);
}

inline void dump (
        const Carrier & carrier,
        const BinaryRelation & rel,
        hdf5::OutFile & file,
        const std::string & name)
{
    POMAGMA_DEBUG("dumping binary/relations/" << name);

    auto word_type = hdf5::Bitfield<Word>::id();

    size_t destin_dim1 = 1 + carrier.item_count();
    size_t destin_dim2 = (carrier.item_count() + BITS_PER_WORD) / BITS_PER_WORD;
    hdf5::Dataspace dataspace(destin_dim1, destin_dim2);

    hdf5::Group group1(file, "relations", true);
    hdf5::Group group2(group1, "binary", true);
    hdf5::Dataset dataset(group2, name, word_type, dataspace);

    size_t source_dim1 = 1 + rel.item_dim();
    size_t source_dim2 = rel.round_word_dim();
    const auto * source = rel.raw_data();
    dataset.write_rectangle(source, source_dim1, source_dim2);

    auto digest = get_hash(carrier, rel);
    hdf5::dump_hash(dataset, digest);
}

inline void dump (
        const Carrier & carrier,
        const NullaryFunction & fun,
        hdf5::OutFile & file,
        const std::string & name)
{
    POMAGMA_DEBUG("dumping functions/nullary/" << name);

    size_t max_ob = carrier.item_count();
    auto ob_type = hdf5::unsigned_type_wide_enough_for(max_ob);

    hdf5::Dataspace dataspace;

    hdf5::Group group1(file, "functions", true);
    hdf5::Group group2(group1, "nullary", true);
    hdf5::Group group3(group2, name, true);
    hdf5::Dataset dataset(group3, "value", ob_type, dataspace);

    Ob data = fun.find();
    POMAGMA_ASSERT_LE(data, max_ob);
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

    POMAGMA_DEBUG("dumping functions/injective/" << name);

    size_t max_ob = carrier.item_count();
    auto ob_type = hdf5::unsigned_type_wide_enough_for(max_ob);

    const size_t destin_dim = 1 + carrier.item_count();
    hdf5::Dataspace dataspace(destin_dim);

    hdf5::Group group1(file, "functions", true);
    hdf5::Group group2(group1, "injective", true);
    hdf5::Group group3(group2, name, true);
    hdf5::Dataset dataset(group3, "value", ob_type, dataspace);

    std::vector<Ob> data(destin_dim, 0);
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

    POMAGMA_DEBUG("dumping functions/" << arity << "/" << name);

    size_t pair_count = fun.count_pairs();
    POMAGMA_DEBUG("dumping " << pair_count << " lhs,rhs pairs");

    typedef uint_<2 * sizeof(Ob)>::t ptr_t;
    size_t max_ob = carrier.item_count();
    size_t max_ptr = pair_count;
    auto ob_type = hdf5::unsigned_type_wide_enough_for(max_ob);
    auto ptr_type = hdf5::unsigned_type_wide_enough_for(max_ptr);

    const size_t destin_dim = 1 + carrier.item_count();
    hdf5::Dataspace ptr_dataspace(destin_dim);
    hdf5::Dataspace ob_dataspace(pair_count);

    hdf5::Group group1(file, "functions", true);
    hdf5::Group group2(group1, arity, true);
    hdf5::Group group3(group2, name, true);
    hdf5::Dataset lhs_ptr_dataset(group3, "lhs_ptr", ptr_type, ptr_dataspace);
    hdf5::Dataset rhs_dataset(group3, "rhs", ob_type, ob_dataspace);
    hdf5::Dataset value_dataset(group3, "value", ob_type, ob_dataspace);

    std::vector<ptr_t> lhs_ptr_data(destin_dim);
    std::vector<Ob> rhs_data(destin_dim);
    std::vector<Ob> value_data(destin_dim);
    ptr_t pos = 0;
    lhs_ptr_data[0] = pos;
    for (Ob lhs = 1; lhs < destin_dim; ++lhs) {
        lhs_ptr_data[lhs] = pos;
        if (carrier.contains(lhs)) {
            rhs_data.clear();
            value_data.clear();
            for (auto rhs = fun.iter_lhs(lhs); rhs.ok(); rhs.next()) {
                if (Function::is_symmetric() and * rhs < lhs) { continue; }
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
    detail::assert_contiguous(carrier);

    // TODO parallelize
    detail::dump(carrier, file);
    for (const auto & pair : signature.unary_relations()) {
        detail::dump(carrier, * pair.second, file, pair.first);
    }
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

} // namespace detail

void hdf5_dump (
        Signature & signature,
        const std::string & filename)
{
    {
        hdf5::GlobalLock lock;
        hdf5::OutFile file(filename);
        detail::dump(signature, file);
    }

    bool readonly = true;
    if (readonly) {
        int info = chmod(filename.c_str(), S_IRUSR | S_IRGRP | S_IROTH);
        POMAGMA_ASSERT(info == 0,
            "chmod(" << filename << " , readonly) failed with code " << info);
    }
}

void protobuf_dump (
        Signature & signature,
        const std::string & filename)
{
    protobuf::Structure structure;

    TODO("add components to structure");

    for (const auto & pair : signature.unary_relations()) {
        auto & rel = * structure.add_unary_relations();
        rel.set_name(pair.first);
    }

    protobuf_dump(structure, filename);
}

void dump (
        Signature & signature,
        const std::string & filename)
{
    POMAGMA_INFO("Dumping structure to file " << filename);

    if (endswith(filename, ".h5")) {
        hdf5_dump(signature, filename);
    } else if (endswith(filename, ".pb") or endswith(filename, ".pb.gz")) {
        protobuf_dump(signature, filename);
    } else {
        POMAGMA_ERROR("unknown file extension: " << filename);
    }

    POMAGMA_INFO("done dumping structure");
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
        hdf5::Dataset dataset(group, "points");
        hdf5::Dataspace dataspace(dataset);
        POMAGMA_ASSERT_EQ(dataspace.rank(), 1);
        std::vector<Ob> data;
        dataset.read_all(data);
        size_t source_item_dim = safe_max_element(data.begin(), data.end());
        size_t destin_item_dim = source_item_dim + extra_item_dim;
        signature.declare(* new Carrier(destin_item_dim));
    }
    Carrier & carrier = * signature.carrier();
    {
        hdf5::Group group1(file, "relations");
        if (group1.exists("unary")) {
            hdf5::Group group2(group1, "unary");
            for (auto name : group2.children()) {
                signature.declare(name, * new UnaryRelation(carrier));
            }
        }
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
        hdf5::Dataset dataset(group, "points");
        hdf5::Dataspace dataspace(dataset);
        POMAGMA_ASSERT_EQ(dataspace.rank(), 1);
        std::vector<Ob> data;
        dataset.read_all(data);
        size_t source_item_dim = safe_max_element(data.begin(), data.end());
        size_t destin_item_dim = carrier.item_dim();
        POMAGMA_ASSERT_LE(source_item_dim, destin_item_dim);
    }
    {
        hdf5::Group group1(file, "relations");
        if (group1.exists("unary")) {
            hdf5::Group group2(group1, "unary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.unary_relation(name),
                    "gdf5 file has unknown unary relation " << name);
            }
        }
        if (group1.exists("binary")) {
            hdf5::Group group2(group1, "binary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.binary_relation(name),
                    "hdf5 file has unknown binary relation " << name);
            }
        }
    }
    {
        hdf5::Group group1(file, "functions");
        {
            hdf5::Group group2(group1, "nullary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.nullary_function(name),
                    "hdf5 file has unknown nullary function " << name);
            }
        }
        if (group1.exists("injective")) {
            hdf5::Group group2(group1, "injective");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.injective_function(name),
                    "hdf5 file has unknown injective function " << name);
            }
        }
        if (group1.exists("binary")) {
            hdf5::Group group2(group1, "binary");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.binary_function(name),
                    "hdf5 file has unknown binary function " << name);
            }
        }
        if (group1.exists("symmetric")) {
            hdf5::Group group2(group1, "symmetric");
            for (auto name : group2.children()) {
                POMAGMA_ASSERT(signature.symmetric_function(name),
                    "hdf5 file has unknown symmetric function " << name);
            }
        }
    }
}

inline void load_data (
        Carrier & carrier,
        hdf5::InFile & file,
        std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("loading carrier");

    hdf5::Group group(file, "carrier");
    hdf5::Dataset dataset(group, "points");

    std::vector<Ob> data;
    dataset.read_all(data);
    Ob max_ob = safe_max_element(data.begin(), data.end());
    POMAGMA_ASSERT_LE(max_ob, carrier.item_dim());
    for (Ob ob : data) {
        carrier.raw_insert(ob);
    }

    hash["carrier"] = hdf5::load_hash(group);
}

inline void update_data (
        Carrier & carrier,
        const std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("updating carrier");

    carrier.update();
    POMAGMA_ASSERT_EQ(carrier.rep_count(), carrier.item_count());
    auto actual = get_hash(carrier);
    auto expected = map_find(hash, "carrier");
    POMAGMA_ASSERT(actual == expected, "carrier is corrupt");

    POMAGMA_INFO("done updating carrier");
}

inline void load_data (
        const Carrier &,
        UnaryRelation & rel,
        hdf5::InFile & file,
        const std::string & name,
        std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("loading unary relation " << name);

    hdf5::Group group1(file, "relations");
    hdf5::Group group2(group1, "unary");
    hdf5::Dataset dataset(group2, name);

    std::vector<Ob> data;
    dataset.read_all(data);
    if (not data.empty()) {
        Ob max_ob = safe_max_element(data.begin(), data.end());
        POMAGMA_ASSERT_LE(max_ob, rel.item_dim());
        rel.clear();
        for (Ob ob : data) {
            rel.raw_insert(ob);
        }
    }

    hash["relations/unary/" + name] = hdf5::load_hash(dataset);
}

inline void update_data (
        const Carrier &,
        UnaryRelation & rel,
        const std::string & name,
        const std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("updating unary relation " << name);

    rel.update();
    auto actual = get_hash(rel);
    auto expected = map_find(hash, "relations/unary/" + name);
    POMAGMA_ASSERT(actual == expected,
            "unary relation " << name << " is corrupt");

    POMAGMA_INFO("done updating unary relation " << name);
}

inline void load_data (
        const Carrier &,
        BinaryRelation & rel,
        hdf5::InFile & file,
        const std::string & name,
        std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("loading binary relation " << name);

    size_t destin_dim1 = 1 + rel.item_dim();
    size_t destin_dim2 = rel.round_word_dim();
    auto * destin = rel.raw_data();

    hdf5::Group group1(file, "relations");
    hdf5::Group group2(group1, "binary");
    hdf5::Dataset dataset(group2, name);

    dataset.read_rectangle(destin, destin_dim1, destin_dim2);

    hash["relations/binary/" + name] = hdf5::load_hash(dataset);
}

inline void update_data (
        const Carrier & carrier,
        BinaryRelation & rel,
        const std::string & name,
        const std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("updating binary relation " << name);

    rel.update();
    auto actual = get_hash(carrier, rel);
    auto expected = map_find(hash, "relations/binary/" + name);
    POMAGMA_ASSERT(actual == expected,
            "binary relation " << name << " is corrupt");

    POMAGMA_INFO("done updating binary relation " << name);
}

inline void load_data (
        const Carrier & carrier,
        NullaryFunction & fun,
        hdf5::InFile & file,
        const std::string & name,
        std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_DEBUG("loading nullary function " << name);

    const size_t item_dim = carrier.item_dim();

    hdf5::Group group1(file, "functions");
    hdf5::Group group2(group1, "nullary");
    hdf5::Group group3(group2, name);
    hdf5::Dataset dataset(group3, "value");

    Ob data;
    dataset.read_scalar(data);
    POMAGMA_ASSERT_LE(data, item_dim);
    fun.raw_insert(data);

    hash["functions/nullary/" + name] = hdf5::load_hash(group3);
}

inline void update_data (
        const Carrier &,
        NullaryFunction & fun,
        const std::string & name,
        const std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_DEBUG("updating nullary function " << name);

    fun.update();
    auto actual = get_hash(fun);
    auto expected = map_find(hash, "functions/nullary/" + name);
    POMAGMA_ASSERT(actual == expected,
            "nullary function " << name << " is corrupt");

    POMAGMA_DEBUG("done updating nullary function " << name);
}

inline void load_data (
        const Carrier & carrier,
        InjectiveFunction & fun,
        hdf5::InFile & file,
        const std::string & name,
        std::unordered_map<std::string, Hasher::Digest> & hash)
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

    hash["functions/injective/"] = hdf5::load_hash(dataset);
}

inline void update_data (
        const Carrier &,
        InjectiveFunction & fun,
        const std::string & name,
        const std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("updating injective function " << name);

    fun.update();
    auto actual = get_hash(fun);
    auto expected = map_find(hash, "functions/injective/" + name);
    POMAGMA_ASSERT(actual == expected,
            "injective function " << name << " is corrupt");

    POMAGMA_INFO("done updating injective function " << name);
}

template<class Function>
inline void load_data (
        const Carrier & carrier,
        Function & fun,
        hdf5::InFile & file,
        const std::string & arity,
        const std::string & name,
        std::unordered_map<std::string, Hasher::Digest> & hash)
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

            rhs_data.resize(count);
            rhs_dataset.read_block(rhs_data, begin);

            value_data.resize(count);
            value_dataset.read_block(value_data, begin);

            for (size_t i = 0; i < count; ++i) {
                fun.raw_insert(lhs, rhs_data[i], value_data[i]);
            }
        }
    }

    hash["functions/" + arity + "/" + name] = hdf5::load_hash(group3);
}

template<class Function>
inline void update_data (
        const Carrier & carrier,
        Function & fun,
        const std::string & arity,
        const std::string & name,
        const std::unordered_map<std::string, Hasher::Digest> & hash)
{
    POMAGMA_INFO("updating " << arity << " function " << name);

    fun.update();
    auto actual = get_hash(carrier, fun);
    auto expected = map_find(hash, "functions/" + arity + "/" + name);
    POMAGMA_ASSERT(actual == expected,
            arity << " function " << name << " is corrupt");

    POMAGMA_INFO("done updating " << arity << " function " << name);
}

inline void load_data (
        Signature & signature,
        hdf5::InFile & file)
{
    POMAGMA_INFO("Loading structure data");

    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    Carrier & carrier = * signature.carrier();

    std::unordered_map<std::string, Hasher::Digest> hash;

    load_data(carrier, file, hash);
    update_data(carrier, hash);

    for (const auto & pair : signature.unary_relations()) {
        load_data(carrier, * pair.second, file, pair.first, hash);
    }
    for (const auto & pair : signature.binary_relations()) {
        load_data(carrier, * pair.second, file, pair.first, hash);
    }
    for (const auto & pair : signature.nullary_functions()) {
        load_data(carrier, * pair.second, file, pair.first, hash);
    }
    for (const auto & pair : signature.injective_functions()) {
        load_data(carrier, * pair.second, file, pair.first, hash);
    }
    for (const auto & pair : signature.binary_functions()) {
        load_data(carrier, * pair.second, file, "binary", pair.first, hash);
    }
    for (const auto & pair : signature.symmetric_functions()) {
        load_data(carrier, * pair.second, file, "symmetric", pair.first, hash);
    }

    std::vector<std::thread> threads;

    // do expensive tasks in parallel
    for (const auto & pair : signature.binary_relations()) {
        threads.push_back(std::thread([&](){
            update_data(carrier, * pair.second, pair.first, hash);
        }));
    }
    for (const auto & pair : signature.binary_functions()) {
        threads.push_back(std::thread([&](){
            update_data(carrier, * pair.second, "binary", pair.first, hash);
        }));
    }
    for (const auto & pair : signature.symmetric_functions()) {
        threads.push_back(std::thread([&](){
            update_data(carrier, * pair.second, "symmetric", pair.first, hash);
        }));
    }

    // do everything else in this thread
    for (const auto & pair : signature.unary_relations()) {
        update_data(carrier, * pair.second, pair.first, hash);
    }
    for (const auto & pair : signature.nullary_functions()) {
        update_data(carrier, * pair.second, pair.first, hash);
    }
    for (const auto & pair : signature.injective_functions()) {
        update_data(carrier, * pair.second, pair.first, hash);
    }

    for (auto & thread : threads) { thread.join(); }
}

} // namespace detail

void hdf5_load (
        Signature & signature,
        const std::string & filename,
        size_t extra_item_dim)
{
    hdf5::GlobalLock lock;
    hdf5::InFile file(filename);

    auto digest = hdf5::get_tree_hash(file);
    POMAGMA_ASSERT(digest == hdf5::load_hash(file), "file is corrupt");

    detail::load_signature(signature, file, extra_item_dim);
    detail::load_data(signature, file);
}

void protobuf_load (
        Signature & signature,
        const std::string & filename,
        size_t extra_item_dim)
{
    const auto structure = protobuf_load<protobuf::Structure>(filename);

    clear(signature);
    size_t source_item_dim = structure.carrier().item_dim();
    size_t destin_item_dim = source_item_dim + extra_item_dim;
    signature.declare(* new Carrier(destin_item_dim));

    TODO("load signature");
    TODO("load data");
}

void load (
        Signature & signature,
        const std::string & filename,
        size_t extra_item_dim)
{
    POMAGMA_INFO("Loading structure from file " << filename);

    if (endswith(filename, ".h5")) {
        hdf5_load(signature, filename, extra_item_dim);
    } else if (endswith(filename, ".pb") or endswith(filename, ".pb.gz")) {
        protobuf_load(signature, filename, extra_item_dim);
    } else {
        POMAGMA_ERROR("unknown file extension: " << filename);
    }

    POMAGMA_INFO("done loading structure");
}

void hdf5_load_data (
        Signature & signature,
        const std::string & filename)
{
    hdf5::GlobalLock lock;
    hdf5::InFile file(filename);

    auto digest = hdf5::get_tree_hash(file);
    POMAGMA_ASSERT(digest == hdf5::load_hash(file), "file is corrupt");

    detail::check_signature(signature, file);
    detail::load_data(signature, file);
}

void protobuf_load_data (
        Signature & signature,
        const std::string & filename)
{
    const auto structure = protobuf_load<protobuf::Structure>(filename);

    POMAGMA_INFO("Loading structure data");

    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    Carrier & carrier = * signature.carrier();

    size_t source_item_dim = structure.carrier().item_dim();
    POMAGMA_ASSERT_LE(source_item_dim, carrier.item_dim());

    TODO("load data");
}

void load_data (
        Signature & signature,
        const std::string & filename)
{
    POMAGMA_INFO("Loading structure from file " << filename);

    if (endswith(filename, ".h5")) {
        hdf5_load_data(signature, filename);
    } else if (endswith(filename, ".pb") or endswith(filename, ".pb.gz")) {
        protobuf_load_data(signature, filename);
    } else {
        POMAGMA_ERROR("unknown file extension: " << filename);
    }

    POMAGMA_INFO("done loading structure");
}

//----------------------------------------------------------------------------
// Logging

void log_stats (Signature & signature)
{
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    Carrier & carrier = * signature.carrier();

    carrier.log_stats();

    for (auto pair : signature.unary_relations()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : signature.binary_relations()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : signature.nullary_functions()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : signature.injective_functions()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : signature.binary_functions()) {
        pair.second->log_stats(pair.first);
    }
    for (auto pair : signature.symmetric_functions()) {
        pair.second->log_stats(pair.first);
    }
}

} // namespace pomagma
