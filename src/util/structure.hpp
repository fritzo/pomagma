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

static Hasher::Digest get_hash (const Carrier & carrier)
{
    Hasher hasher;
    for (auto i = carrier.iter(); i.ok(); i.next()) {
        uint32_t data = * i;
        hasher.add(data);
    }
    return hasher.finish();
}

static Hasher::Digest get_hash (
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

static Hasher::Digest get_hash (const NullaryFunction & fun)
{
    std::array<uint32_t, 1> tuple;
    tuple[0] = fun.find();
    return Hasher::digest(tuple);
}

static Hasher::Digest get_hash (const InjectiveFunction & fun)
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

static Hasher::Digest get_hash (
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

static Hasher::Digest get_hash (
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

} // namespace pomagma
