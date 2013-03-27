#include "aggregate.hpp"
#include "carrier.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include "scheduler.hpp"

namespace pomagma
{

namespace detail
{

void copy_one (
        BinaryRelation & destin_rel,
        const BinaryRelation & src_rel,
        const Carrier & src_carrier,
        const std::vector<Ob> & translate)
{
    for (auto iter = src_carrier.iter(); iter.ok(); iter.next()) {
        Ob src_lhs = * iter;
        Ob destin_lhs = translate[src_lhs];
        for (auto iter = src_rel.iter_lhs(src_lhs); iter.ok(); iter.next()) {
            Ob src_rhs = * iter;
            Ob destin_rhs = translate[src_rhs];
            destin_rel.insert(destin_lhs, destin_rhs);
        }
    }
}

void copy_one (
        NullaryFunction & destin_fun,
        const NullaryFunction & src_fun,
        const Carrier & src_carrier __attribute__((unused)),
        const std::vector<Ob> & translate)
{
    if (Ob src_val = src_fun.find()) {
        Ob destin_val = translate[src_val];
        destin_fun.insert(destin_val);
    }
}

void copy_one (
        InjectiveFunction & destin_fun,
        const InjectiveFunction & src_fun,
        const Carrier & src_carrier __attribute__((unused)),
        const std::vector<Ob> & translate)
{
    for (auto iter = src_fun.iter(); iter.ok(); iter.next()) {
        Ob src_arg = * iter;
        Ob src_val = src_fun.find(src_arg);
        Ob destin_arg = translate[src_arg];
        Ob destin_val = translate[src_val];
        destin_fun.insert(destin_arg, destin_val);
    }
}

template<class Function>
void copy_one (
        Function & destin_fun,
        const Function & src_fun,
        const Carrier & src_carrier,
        const std::vector<Ob> & translate)
{
    for (auto iter = src_carrier.iter(); iter.ok(); iter.next()) {
        Ob src_lhs = * iter;
        Ob destin_lhs = translate[src_lhs];
        for (auto iter = src_fun.iter_lhs(src_lhs); iter.ok(); iter.next()) {
            Ob src_rhs = * iter;
            if (Function::is_symmetric() and src_rhs < src_lhs) { continue; }
            Ob src_val = src_fun.find(src_lhs, src_rhs);
            Ob destin_rhs = translate[src_rhs];
            Ob destin_val = translate[src_val];
            destin_fun.insert(destin_lhs, destin_rhs, destin_val);
        }
    }
}

template<class T>
void copy_all (
        const std::unordered_map<std::string, T *> & destin_map,
        const std::unordered_map<std::string, T *> & src_map,
        const Carrier & src_carrier,
        const std::vector<Ob> & translate)
{

    for (auto pair : destin_map) {
        auto & name = pair.first;
        auto & destin = * pair.second;
        auto i = src_map.find(name);
        if (i == src_map.end()) {
            POMAGMA_WARN("missing " << name);
        } else {
            POMAGMA_INFO("aggregating " << name);
            auto & src = * i->second;
            copy_one(destin, src, src_carrier, translate);
        }
    }
}

} // namespace detail

void aggregate (
        Structure & destin,
        Structure & src,
        bool clear_src)
{
    POMAGMA_INFO("Aggregating structure");

    POMAGMA_ASSERT(& destin != & src, "cannot aggregate structure into self");
    POMAGMA_ASSERT_LE(
            destin.carrier().item_count() + src.carrier().item_count(),
            destin.carrier().item_dim());

    std::vector<Ob> translate(1 + src.carrier().item_dim(), 0);
    destin.carrier().set_merge_callback(schedule_merge);
    for (auto iter = src.carrier().iter(); iter.ok(); iter.next()) {
        translate[*iter] = destin.carrier().unsafe_insert();
    }

#define POMAGMA_COPY_ALL(arity)\
    detail::copy_all(\
            destin.signature().arity(),\
            src.signature().arity(),\
            src.carrier(),\
            translate)

    POMAGMA_COPY_ALL(binary_relations);
    POMAGMA_COPY_ALL(nullary_functions);
    POMAGMA_COPY_ALL(injective_functions);
    POMAGMA_COPY_ALL(binary_functions);
    POMAGMA_COPY_ALL(symmetric_functions);

#undef POMAGMA_COPY_ALL

    if (clear_src) { src.clear(); }

    process_mergers(destin.signature());
}

} // namespace pomagma
