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
#include <algorithm>
#include <array>
#include <pomagma/atlas/structure.pb.h>
#include <pomagma/atlas/protobuf.hpp>
#include <pomagma/io/protoblob.hpp>
#include <thread>

namespace pomagma {

//----------------------------------------------------------------------------
// Interface

void validate_consistent(Signature &signature);
void validate(Signature &signature);
void clear(Signature &signature);
void clear_data(Signature &signature);
void log_stats(Signature &signature);

void dump(Signature &signature, const std::string &filename);

void load(Signature &signature, const std::string &filename,
          size_t extra_item_dim = 0);

void load_data(Signature &signature, const std::string &filename);

//----------------------------------------------------------------------------
// Validation

void validate_consistent(Signature &signature) {
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    for (auto i : signature.unary_relations()) {
        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            auto *pos = i.second;
            if (auto *neg = signature.unary_relation(negated)) {
                pos->validate_disjoint(*neg);
            }
        }
    }
    for (auto i : signature.binary_relations()) {
        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            auto *pos = i.second;
            if (auto *neg = signature.binary_relation(negated)) {
                pos->validate_disjoint(*neg);
            }
        }
    }
}

void validate(Signature &signature) {
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    std::vector<std::thread> threads;

    // do expensive tasks in parallel
    for (auto i : signature.binary_relations()) {
        auto *pos = i.second;
        threads.push_back(std::thread([pos]() { pos->validate(); }));

        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            if (auto *neg = signature.binary_relation(negated)) {
                threads.push_back(std::thread([pos, neg]() {
                    pos->validate_disjoint(*neg);
                }));
            }
        }
    }
    for (auto i : signature.binary_functions()) {
        auto *fun = i.second;
        threads.push_back(std::thread([fun]() { fun->validate(); }));
    }
    for (auto i : signature.symmetric_functions()) {
        auto *fun = i.second;
        threads.push_back(std::thread([fun]() { fun->validate(); }));
    }

    // do everything else in this thread
    for (auto i : signature.unary_relations()) {
        auto *pos = i.second;
        pos->validate();

        std::string name = i.first;
        std::string negated = signature.negate(name);
        if (name < negated) {
            if (auto *neg = signature.unary_relation(negated)) {
                pos->validate_disjoint(*neg);
            }
        }
    }
    for (auto i : signature.injective_functions()) {
        auto *fun = i.second;
        fun->validate();
    }
    for (auto i : signature.nullary_functions()) {
        auto *fun = i.second;
        fun->validate();
    }
    signature.carrier()->validate();

    for (auto &thread : threads) {
        thread.join();
    }
}

//----------------------------------------------------------------------------
// Clearing

void clear(Signature &signature) {
    POMAGMA_INFO("Clearing signature");

    if (signature.carrier()) {
        for (auto i : signature.unary_relations()) {
            delete i.second;
        }
        for (auto i : signature.binary_relations()) {
            delete i.second;
        }
        for (auto i : signature.nullary_functions()) {
            delete i.second;
        }
        for (auto i : signature.injective_functions()) {
            delete i.second;
        }
        for (auto i : signature.binary_functions()) {
            delete i.second;
        }
        for (auto i : signature.symmetric_functions()) {
            delete i.second;
        }
        delete signature.carrier();
    }
    signature.clear();
}

void clear_data(Signature &signature) {
    POMAGMA_INFO("Clearing signature data");
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");

    if (signature.carrier()->item_count()) {
        for (auto i : signature.unary_relations()) {
            i.second->clear();
        }
        for (auto i : signature.binary_relations()) {
            i.second->clear();
        }
        for (auto i : signature.nullary_functions()) {
            i.second->clear();
        }
        for (auto i : signature.injective_functions()) {
            i.second->clear();
        }
        for (auto i : signature.binary_functions()) {
            i.second->clear();
        }
        for (auto i : signature.symmetric_functions()) {
            i.second->clear();
        }
        signature.carrier()->clear();
    }
}

//----------------------------------------------------------------------------
// Hashing

namespace detail {

inline Hasher::Digest get_hash(const Carrier &carrier) {
    Hasher hasher;
    for (auto i = carrier.iter(); i.ok(); i.next()) {
        uint32_t data = *i;
        hasher.add(data);
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash(const UnaryRelation &rel) {
    Hasher hasher;
    for (auto i = rel.iter(); i.ok(); i.next()) {
        uint32_t data = *i;
        hasher.add(data);
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash(const Carrier &carrier,
                               const BinaryRelation &rel) {
    // TODO parallelize
    std::vector<std::pair<uint32_t, Hasher::Digest>> rows;
    for (auto lhs = carrier.iter(); lhs.ok(); lhs.next()) {
        bool empty = true;
        Hasher hasher;
        for (auto rhs = rel.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
            empty = false;
            hasher.add(static_cast<uint32_t>(*rhs));
        }
        hasher.finish();
        if (not empty) {
            rows.push_back({*lhs, hasher.data()});
        }
    }
    return Hasher::digest(rows);
}

inline Hasher::Digest get_hash(const NullaryFunction &fun) {
    std::array<uint32_t, 1> tuple;
    tuple[0] = fun.find();
    return Hasher::digest(tuple);
}

inline Hasher::Digest get_hash(const InjectiveFunction &fun) {
    Hasher hasher;
    std::array<uint32_t, 2> tuple;
    for (auto key = fun.iter(); key.ok(); key.next()) {
        tuple[0] = *key;
        tuple[1] = fun.find(*key);
        hasher.add(tuple);
    }
    return hasher.finish();
}

inline Hasher::Digest get_hash(const Carrier &carrier,
                               const BinaryFunction &fun) {
    // TODO parallelize
    std::vector<std::pair<uint32_t, Hasher::Digest>> rows;
    for (auto lhs = carrier.iter(); lhs.ok(); lhs.next()) {
        bool empty = true;
        Hasher hasher;
        for (auto rhs = fun.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
            empty = false;
            hasher.add(static_cast<uint32_t>(*rhs));
            hasher.add(static_cast<uint32_t>(fun.find(*lhs, *rhs)));
        }
        hasher.finish();
        if (not empty) {
            rows.push_back({*lhs, hasher.data()});
        }
    }
    return Hasher::digest(rows);
}

inline Hasher::Digest get_hash(const Carrier &carrier,
                               const SymmetricFunction &fun) {
    // TODO parallelize
    std::vector<std::pair<uint32_t, Hasher::Digest>> rows;
    for (auto lhs = carrier.iter(); lhs.ok(); lhs.next()) {
        bool empty = true;
        Hasher hasher;
        for (auto rhs = fun.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
            if (*rhs > *lhs) {
                break;
            }
            empty = false;
            hasher.add(static_cast<uint32_t>(*rhs));
            hasher.add(static_cast<uint32_t>(fun.find(*lhs, *rhs)));
        }
        hasher.finish();
        if (not empty) {
            rows.push_back({*lhs, hasher.data()});
        }
    }
    return Hasher::digest(rows);
}

}  // namespace detail

//----------------------------------------------------------------------------
// Dumping

namespace detail {

inline void assert_contiguous(const Carrier &carrier) {
    size_t max_item = 0;
    size_t item_count = 0;
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        max_item = *iter;
        ++item_count;
    }
    POMAGMA_ASSERT(max_item == item_count,
                   "dumping requires contiguous carrier; try compacting first");
}

inline void dump(const Carrier &carrier, protobuf::Structure &structure,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping carrier");
    const std::string hash = Hasher::str(get_hash(carrier));

    mutex.lock();
    auto &message = *structure.mutable_carrier();
    message.set_hash(hash);
    message.set_item_count(carrier.item_count());
    mutex.unlock();
}

inline void dump(const Carrier &, const UnaryRelation &rel,
                 protobuf::Structure &structure, const std::string &name,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping unary relation " << name);
    const std::string hash = Hasher::str(get_hash(rel));

    mutex.lock();
    auto &message = *structure.add_unary_relations();
    message.set_name(name);
    message.set_hash(hash);
    mutex.unlock();

    // write blob with a single chunk
    protobuf::BlobWriter blob([&](const std::string &hexdigest) {
        std::unique_lock<std::mutex> lock(mutex);
        *message.add_blobs() = hexdigest;
    });
    protobuf::UnaryRelation chunk;
    protobuf::dump(rel.get_set(), *chunk.mutable_set());
    blob.write(chunk);
}

inline void dump(const Carrier &carrier, const BinaryRelation &rel,
                 protobuf::Structure &structure, const std::string &name,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping binary relation " << name);
    const std::string hash = Hasher::str(get_hash(carrier, rel));

    mutex.lock();
    auto &message = *structure.add_binary_relations();
    message.set_name(name);
    message.set_hash(hash);
    mutex.unlock();

    // write a single blob chunked by row
    protobuf::BlobWriter blob([&](const std::string &hexdigest) {
        std::unique_lock<std::mutex> lock(mutex);
        *message.add_blobs() = hexdigest;
    });
    protobuf::BinaryRelation chunk;
    protobuf::BinaryRelation::Row &chunk_row = *chunk.add_rows();
    for (auto lhs = carrier.support().iter(); lhs.ok(); lhs.next()) {
        if (unlikely(*lhs % 512 == 0)) {
            blob.try_split();
        }
        chunk_row.set_lhs(*lhs);
        protobuf::dump(rel.get_Lx_set(*lhs), *chunk_row.mutable_rhs());
        blob.write(chunk);
    }
}

inline void dump(const Carrier &, const NullaryFunction &fun,
                 protobuf::Structure &structure, const std::string &name,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping nullary function " << name);
    const std::string hash = Hasher::str(get_hash(fun));

    mutex.lock();
    auto &message = *structure.add_nullary_functions();
    message.set_name(name);
    message.set_hash(hash);
    if (Ob val = fun.find()) {
        message.set_val(val);
    }
    mutex.unlock();
}

inline void dump(const Carrier &, const InjectiveFunction &fun,
                 protobuf::Structure &structure, const std::string &name,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping injective function " << name);
    const std::string hash = Hasher::str(get_hash(fun));

    mutex.lock();
    auto &message = *structure.add_injective_functions();
    message.set_name(name);
    message.set_hash(hash);
    mutex.unlock();

    // write blob with a single chunk
    protobuf::BlobWriter blob([&](const std::string &hexdigest) {
        std::unique_lock<std::mutex> lock(mutex);
        *message.add_blobs() = hexdigest;
    });
    protobuf::UnaryFunction chunk;
    protobuf::ObMap &chunk_map = *chunk.mutable_map();
    for (auto key = fun.iter(); key.ok(); key.next()) {
        chunk_map.add_key(*key);
        chunk_map.add_val(fun.raw_find(*key));
    }
    protobuf::delta_compress(chunk_map);
    blob.write(chunk);
}

inline void dump(const Carrier &carrier, const BinaryFunction &fun,
                 protobuf::Structure &structure, const std::string &name,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping binary function " << name);
    const std::string hash = Hasher::str(get_hash(carrier, fun));

    mutex.lock();
    auto &message = *structure.add_binary_functions();
    message.set_name(name);
    message.set_hash(hash);
    mutex.unlock();

    // write a single blob chunked by row
    protobuf::BlobWriter blob([&](const std::string &hexdigest) {
        std::unique_lock<std::mutex> lock(mutex);
        *message.add_blobs() = hexdigest;
    });
    protobuf::BinaryFunction chunk;
    protobuf::BinaryFunction::Row &chunk_row = *chunk.add_rows();
    protobuf::ObMap &rhs_val = *chunk_row.mutable_rhs_val();
    for (auto lhs = carrier.support().iter(); lhs.ok(); lhs.next()) {
        if (unlikely(*lhs % 512 == 0)) {
            blob.try_split();
        }
        chunk_row.set_lhs(*lhs);
        rhs_val.Clear();
        for (auto rhs = fun.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
            rhs_val.add_key(*rhs);
            rhs_val.add_val(fun.raw_find(*lhs, *rhs));
        }
        protobuf::delta_compress(rhs_val);
        blob.write(chunk);
    }
}

inline void dump(const Carrier &carrier, const SymmetricFunction &fun,
                 protobuf::Structure &structure, const std::string &name,
                 std::mutex &mutex) {
    POMAGMA_DEBUG("dumping symmetric function " << name);
    const std::string hash = Hasher::str(get_hash(carrier, fun));

    mutex.lock();
    auto &message = *structure.add_symmetric_functions();
    message.set_name(name);
    message.set_hash(hash);
    mutex.unlock();

    // write a single blob chunked by row
    protobuf::BlobWriter blob([&](const std::string &hexdigest) {
        std::unique_lock<std::mutex> lock(mutex);
        *message.add_blobs() = hexdigest;
    });
    protobuf::BinaryFunction chunk;
    protobuf::BinaryFunction::Row &chunk_row = *chunk.add_rows();
    protobuf::ObMap &rhs_val = *chunk_row.mutable_rhs_val();
    for (auto lhs = carrier.support().iter(); lhs.ok(); lhs.next()) {
        if (unlikely(*lhs % 512 == 0)) {
            blob.try_split();
        }
        chunk_row.set_lhs(*lhs);
        rhs_val.Clear();
        for (auto rhs = fun.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
            if (*rhs > *lhs) break;
            rhs_val.add_key(*rhs);
            rhs_val.add_val(fun.raw_find(*lhs, *rhs));
        }
        protobuf::delta_compress(rhs_val);
        blob.write(chunk);
    }
}

inline Hasher::Dict get_tree_hash(const protobuf::Structure &structure) {
    Hasher::Dict dict;

    POMAGMA_ASSERT(structure.carrier().has_hash(), "carrier is missing hash");
    dict["carrier"] = parse_digest(structure.carrier().hash());

#define CASE_ARITY(Kind, kind, Arity, arity)                             \
    for (const auto &i : structure.arity##_##kind##s()) {                \
        POMAGMA_ASSERT(i.has_name(), #Arity #Kind " is missing name");   \
        POMAGMA_ASSERT(i.has_hash(), #Arity #Kind " is missing hash");   \
        dict[#kind "s/" #arity "/" + i.name()] = parse_digest(i.hash()); \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY

    return dict;
}

inline void dump(Signature &signature, protobuf::Structure &structure,
                 std::vector<std::string> &sub_hexdigests) {
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    const Carrier &carrier = *signature.carrier();
    detail::assert_contiguous(carrier);

    std::mutex mutex;
    std::vector<std::thread> threads;

    threads.push_back(
        std::thread([&] { detail::dump(carrier, structure, mutex); }));

#define CASE_ARITY(Kind, kind, Arity, arity)                             \
    for (const auto &i : signature.arity##_##kind##s()) {                \
        threads.push_back(std::thread([&] {                              \
            detail::dump(carrier, *i.second, structure, i.first, mutex); \
        }));                                                             \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY

    for (auto &thread : threads) {
        thread.join();
    }

#define CASE_ARITY(Kind, kind, Arity, arity)              \
    for (const auto &i : structure.arity##_##kind##s()) { \
        for (const std::string &blob : i.blobs()) {       \
            sub_hexdigests.push_back(blob);               \
        }                                                 \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY

    auto digest = Hasher::digest(get_tree_hash(structure));
    structure.set_hash(Hasher::str(digest));
}

}  // namespace detail

void dump(Signature &signature, const std::string &filename) {
    POMAGMA_INFO("Dumping structure to file " << filename);
    POMAGMA_ASSERT_EQ(fs::extension(filename), ".pb");

    protobuf::Structure structure;

    std::vector<std::string> sub_hexdigests;
    detail::dump(signature, structure, sub_hexdigests);

    protobuf::BlobWriter([&](const std::string &hexdigest) {
                             dump_blob_ref(hexdigest, filename, sub_hexdigests);
                         }).write(structure);

    POMAGMA_INFO("done dumping structure");
}

//----------------------------------------------------------------------------
// Loading

namespace detail {

inline void update_data(Carrier &carrier, const Hasher::Dict &hash) {
    POMAGMA_INFO("updating carrier");

    carrier.update();
    POMAGMA_ASSERT_EQ(carrier.rep_count(), carrier.item_count());
    auto actual = get_hash(carrier);
    auto expected = map_find(hash, "carrier");
    POMAGMA_ASSERT(actual == expected, "carrier is corrupt");

    POMAGMA_INFO("done updating carrier");
}

inline void update_data(const Carrier &, UnaryRelation &rel,
                        const std::string &name, const Hasher::Dict &hash) {
    POMAGMA_INFO("updating unary relation " << name);

    rel.update();
    auto actual = get_hash(rel);
    auto expected = map_find(hash, "relations/unary/" + name);
    POMAGMA_ASSERT(actual == expected, "unary relation " << name
                                                         << " is corrupt");

    POMAGMA_INFO("done updating unary relation " << name);
}

inline void update_data(const Carrier &carrier, BinaryRelation &rel,
                        const std::string &name, const Hasher::Dict &hash) {
    POMAGMA_INFO("updating binary relation " << name);

    rel.update();
    auto expected = map_find(hash, "relations/binary/" + name);
    auto actual = get_hash(carrier, rel);
    POMAGMA_ASSERT(actual == expected, "binary relation " << name
                                                          << " is corrupt");

    POMAGMA_INFO("done updating binary relation " << name);
}

inline void update_data(const Carrier &, NullaryFunction &fun,
                        const std::string &name, const Hasher::Dict &hash) {
    POMAGMA_DEBUG("updating nullary function " << name);

    fun.update();
    auto actual = get_hash(fun);
    auto expected = map_find(hash, "functions/nullary/" + name);
    POMAGMA_ASSERT(actual == expected, "nullary function " << name
                                                           << " is corrupt");

    POMAGMA_DEBUG("done updating nullary function " << name);
}

inline void update_data(const Carrier &, InjectiveFunction &fun,
                        const std::string &name, const Hasher::Dict &hash) {
    POMAGMA_INFO("updating injective function " << name);

    fun.update();
    auto actual = get_hash(fun);
    auto expected = map_find(hash, "functions/injective/" + name);
    POMAGMA_ASSERT(actual == expected, "injective function " << name
                                                             << " is corrupt");

    POMAGMA_INFO("done updating injective function " << name);
}

template <class Function>
inline void update_data(const Carrier &carrier, Function &fun,
                        const std::string &arity, const std::string &name,
                        const Hasher::Dict &hash) {
    POMAGMA_INFO("updating " << arity << " function " << name);

    fun.update();
    auto actual = get_hash(carrier, fun);
    auto expected = map_find(hash, "functions/" + arity + "/" + name);
    POMAGMA_ASSERT(actual == expected, arity << " function " << name
                                             << " is corrupt");

    POMAGMA_INFO("done updating " << arity << " function " << name);
}

void update_functions_and_relations(Signature &signature,
                                    const Carrier &carrier,
                                    const Hasher::Dict &hash) {
    std::vector<std::thread> threads;

    // do expensive tasks in parallel
    for (const auto &pair : signature.binary_relations()) {
        threads.push_back(std::thread([&]() {
            update_data(carrier, *pair.second, pair.first, hash);
        }));
    }
    for (const auto &pair : signature.binary_functions()) {
        threads.push_back(std::thread([&]() {
            update_data(carrier, *pair.second, "binary", pair.first, hash);
        }));
    }
    for (const auto &pair : signature.symmetric_functions()) {
        threads.push_back(std::thread([&]() {
            update_data(carrier, *pair.second, "symmetric", pair.first, hash);
        }));
    }

    // do everything else in this thread
    for (const auto &pair : signature.unary_relations()) {
        update_data(carrier, *pair.second, pair.first, hash);
    }
    for (const auto &pair : signature.nullary_functions()) {
        update_data(carrier, *pair.second, pair.first, hash);
    }
    for (const auto &pair : signature.injective_functions()) {
        update_data(carrier, *pair.second, pair.first, hash);
    }

    for (auto &thread : threads) {
        thread.join();
    }
}

inline void call_or_defer(std::vector<std::function<void()>> *defer,
                          std::function<void()> fun) {
    if (defer) {
        defer->push_back(fun);
    } else {
        fun();
    }
}

inline void load_signature(Signature &signature,
                           const protobuf::Structure &structure,
                           size_t extra_item_dim) {
    POMAGMA_INFO("Loading signature");

    clear(signature);
    size_t item_dim = structure.carrier().item_count() + extra_item_dim;
    signature.declare(*new Carrier(item_dim));
    Carrier &carrier = *signature.carrier();

#define CASE_ARITY(Kind, kind, Arity, arity)                           \
    for (const auto &i : structure.arity##_##kind##s()) {              \
        POMAGMA_ASSERT(i.has_name(), #Arity #Kind " is missing name"); \
        signature.declare(i.name(), *new Arity##Kind(carrier));        \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY
}

// check that all structure in file is already contained in signature
inline void check_signature(Signature &signature,
                            const protobuf::Structure &structure) {
    POMAGMA_INFO("Checking signature");

    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    const Carrier &carrier = *signature.carrier();
    size_t item_count = structure.carrier().item_count();
    size_t item_dim = carrier.item_dim();
    POMAGMA_ASSERT_LE(item_count, item_dim);

#define CASE_ARITY(Kind, kind, Arity, arity)                                  \
    for (const auto &i : structure.arity##_##kind##s()) {                     \
        POMAGMA_ASSERT(i.has_name(), #Arity #Kind " is missing name");        \
        POMAGMA_ASSERT(signature.arity##_##kind(i.name()),                    \
                       "file has unknown " #arity " " #kind " " << i.name()); \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY
}

inline void load_data(Carrier &carrier, const protobuf::Carrier &message) {
    POMAGMA_INFO("loading carrier");

    size_t item_count = message.item_count();
    POMAGMA_ASSERT_LE(item_count, carrier.item_dim());
    for (Ob ob = 1; ob <= item_count; ++ob) {
        carrier.raw_insert(ob);
    }
}

inline void load_data(UnaryRelation &rel,
                      const protobuf::UnaryRelation &message,
                      std::vector<std::function<void()>> *tasks = nullptr) {
    // load data in message
    if (message.has_set()) {
        POMAGMA_ASSERT1(message.set().IsInitialized(),
                        "dense is not initialized");
        protobuf::load(rel.raw_set(), message.set());
    }

    // recurse to blobs pointed to by message
    call_or_defer(tasks, [&] {
        for (const auto &hexdigest : message.blobs()) {
            protobuf::BlobReader blob(hexdigest);
            protobuf::UnaryRelation chunk;
            while (blob.try_read_chunk(chunk)) {
                load_data(rel, chunk);
                chunk.Clear();
            }
        }
    });
}

inline void load_data(BinaryRelation &rel,
                      const protobuf::BinaryRelation &message,
                      std::vector<std::function<void()>> *tasks = nullptr) {
    // load data in message
    for (const auto &row : message.rows()) {
        POMAGMA_ASSERT1(row.IsInitialized(), "row is not initialized");
        DenseSet rhs = rel.get_Lx_set(row.lhs());
        protobuf::load(rhs, row.rhs());
    }

    // recurse to blobs pointed to by message
    for (const auto &hexdigest : message.blobs()) {
        call_or_defer(tasks, [&] {
            protobuf::BlobReader blob(hexdigest);
            protobuf::BinaryRelation chunk;
            while (blob.try_read_chunk(chunk)) {
                load_data(rel, chunk);
                chunk.Clear();
            }
        });
    }
}

inline void load_data(NullaryFunction &fun,
                      const protobuf::NullaryFunction &message,
                      std::vector<std::function<void()>> *) {
    if (message.has_val()) {
        fun.raw_insert(message.val());
    }
}

// message is nonconst to support in-place decompression
inline void load_data(InjectiveFunction &fun, protobuf::UnaryFunction &message,
                      std::vector<std::function<void()>> *tasks = nullptr) {
    // load data in message
    if (message.has_map()) {
        auto &map = *message.mutable_map();
        protobuf::delta_decompress(map);
        POMAGMA_ASSERT_EQ(map.key_size(), map.val_size());
        for (size_t i = 0, size = map.key_size(); i < size; ++i) {
            fun.raw_insert(map.key(i), map.val(i));
        }
    }

    // recurse to blobs pointed to by message
    call_or_defer(tasks, [&] {
        for (const auto &hexdigest : message.blobs()) {
            protobuf::BlobReader blob(hexdigest);
            protobuf::UnaryFunction chunk;
            while (blob.try_read_chunk(chunk)) {
                load_data(fun, chunk);
                chunk.Clear();
            }
        }
    });
}

// message is nonconst to support in-place decompression
inline void load_data(BinaryFunction &fun, protobuf::BinaryFunction &message,
                      std::vector<std::function<void()>> *tasks = nullptr) {
    // load data in message
    for (auto &row : *message.mutable_rows()) {
        POMAGMA_ASSERT1(row.IsInitialized(), "row is not initialized");
        const Ob lhs = row.lhs();
        auto &rhs_val = *row.mutable_rhs_val();
        protobuf::delta_decompress(rhs_val);
        POMAGMA_ASSERT_EQ(rhs_val.key_size(), rhs_val.val_size());

        fun.raw_lock();
        for (size_t i = 0, size = rhs_val.key_size(); i < size; ++i) {
            fun.raw_insert(lhs, rhs_val.key(i), rhs_val.val(i));
        }
        fun.raw_unlock();
    }

    // recurse to blobs pointed to by message
    for (const auto &hexdigest : message.blobs()) {
        call_or_defer(tasks, [&] {
            protobuf::BlobReader blob(hexdigest);
            protobuf::BinaryFunction chunk;
            while (blob.try_read_chunk(chunk)) {
                load_data(fun, chunk);
                chunk.Clear();
            }
        });
    }
}

// message is nonconst to support in-place decompression
inline void load_data(SymmetricFunction &fun, protobuf::BinaryFunction &message,
                      std::vector<std::function<void()>> *tasks = nullptr) {
    // load data in message
    for (auto &row : *message.mutable_rows()) {
        POMAGMA_ASSERT1(row.IsInitialized(), "row is not initialized");
        const Ob lhs = row.lhs();
        auto &rhs_val = *row.mutable_rhs_val();
        protobuf::delta_decompress(rhs_val);
        POMAGMA_ASSERT_EQ(rhs_val.key_size(), rhs_val.val_size());

        fun.raw_lock();
        for (size_t i = 0, size = rhs_val.key_size(); i < size; ++i) {
            fun.raw_insert(rhs_val.key(i), lhs, rhs_val.val(i));
        }
        fun.raw_unlock();
    }

    // recurse to blobs pointed to by message
    for (const auto &hexdigest : message.blobs()) {
        call_or_defer(tasks, [&] {
            protobuf::BlobReader blob(hexdigest);
            protobuf::BinaryFunction chunk;
            while (blob.try_read_chunk(chunk)) {
                load_data(fun, chunk);
                chunk.Clear();
            }
        });
    }
}

inline void load_data(Signature &signature, protobuf::Structure &structure) {
    POMAGMA_INFO("Loading structure data");

    const Hasher::Dict hash = get_tree_hash(structure);

    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    Carrier &carrier = *signature.carrier();
    load_data(carrier, structure.carrier());
    update_data(carrier, hash);

    std::vector<std::function<void()>> tasks;

#define CASE_ARITY(Kind, kind, Arity, arity)                           \
    for (auto &i : *structure.mutable_##arity##_##kind##s()) {         \
        POMAGMA_ASSERT(i.has_name(), #Arity #Kind " is missing name"); \
        POMAGMA_INFO("loading " #Arity #Kind " " << i.name());         \
        load_data(*signature.arity##_##kind(i.name()), i, &tasks);     \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY

#pragma omp parallel for schedule(dynamic, 1)
    for (size_t i = 0; i < tasks.size(); ++i) {
        tasks[i]();
    }

    // TODO move this work into the parallel tasks.
    update_functions_and_relations(signature, carrier, hash);
}

}  // namespace detail

void load(Signature &signature, const std::string &filename,
          size_t extra_item_dim) {
    POMAGMA_INFO("Loading structure from file " << filename);
    POMAGMA_ASSERT_EQ(fs::extension(filename), ".pb");

    protobuf::Structure structure;
    POMAGMA_ASSERT(structure.descriptor(), "protobuf error");
    protobuf::InFile(find_blob(load_blob_ref(filename))).read(structure);

    POMAGMA_ASSERT(structure.has_hash(), "structure is missing hash");
    auto digest = Hasher::digest(detail::get_tree_hash(structure));
    POMAGMA_ASSERT(Hasher::str(digest) == structure.hash(), "file is corrupt");

    detail::load_signature(signature, structure, extra_item_dim);
    detail::load_data(signature, structure);

    POMAGMA_INFO("done loading structure");
}

void load_data(Signature &signature, const std::string &filename) {
    POMAGMA_INFO("Loading structure from file " << filename);
    POMAGMA_ASSERT_EQ(fs::extension(filename), ".pb");

    protobuf::Structure structure;
    POMAGMA_ASSERT(structure.descriptor(), "protobuf error");
    protobuf::InFile(find_blob(load_blob_ref(filename))).read(structure);

    POMAGMA_ASSERT(structure.has_hash(), "structure is missing hash");
    auto digest = Hasher::digest(detail::get_tree_hash(structure));
    POMAGMA_ASSERT(Hasher::str(digest) == structure.hash(), "file is corrupt");

    detail::load_data(signature, structure);

    POMAGMA_INFO("done loading structure");
}

//----------------------------------------------------------------------------
// Logging

void log_stats(Signature &signature) {
    POMAGMA_ASSERT(signature.carrier(), "carrier is not defined");
    Carrier &carrier = *signature.carrier();

    carrier.log_stats();

#define CASE_ARITY(Kind, kind, Arity, arity)          \
    for (auto pair : signature.arity##_##kind##s()) { \
        pair.second->log_stats(pair.first);           \
    }
    POMAGMA_SWITCH_ARITY(CASE_ARITY)
#undef CASE_ARITY
}

}  // namespace pomagma
