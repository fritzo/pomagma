#include "trim.hpp"
#include "carrier.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include "parser.hpp"
#include "sampler.hpp"

namespace pomagma
{

namespace detail
{

void insert_nullary_functions (
        Structure & structure,
        DenseSet & subset,
        size_t target_item_count)
{
    for (auto pair : structure.signature().nullary_functions()) {
        auto fun = pair.second;
        if (Ob val = fun->find()) {
            subset.insert(val);
        }
    }
    POMAGMA_ASSERT_LE(subset.count_items(), target_item_count);
}

void assume (
        Parser & parser,
        Parser::Policy & policy,
        const std::string & expression_str)
{
    POMAGMA_DEBUG("assume " << expression_str);
    std::istringstream expression(expression_str);

    std::string type;
    POMAGMA_ASSERT(getline(expression, type, ' '), "bad line: " << expression);
    Ob lhs = parser.parse_insert(expression, policy);
    Ob rhs = parser.parse_insert(expression, policy);
    POMAGMA_ASSERT(lhs and rhs, "parse_insert failed");

    POMAGMA_ASSERT(
            (type == "EQUAL") or (type == "LESS") or (type == "NLESS"),
            "bad relation type: " << type);
}

void assume_core_facts (
        Structure & structure,
        DenseSet & subset,
        size_t target_item_count,
        const char * theory_file)
{
    POMAGMA_INFO("assuming core facts");
    std::ifstream file(theory_file);
    POMAGMA_ASSERT(file, "failed to open " << theory_file);

    Parser parser(structure.signature());
    Parser::Policy policy(subset, target_item_count);
    std::string expression;
    while (getline(file, expression)) {
        if (not expression.empty() and expression[0] != '#') {
            assume(parser, policy, expression);
        }
    }
}

void fill_random(
        Structure & structure,
        DenseSet & subset,
        size_t target_item_count,
        const char * language_file)
{
    POMAGMA_INFO("filling randomly facts");
    std::random_device device;
    rng_t rng(device());
    Sampler sampler(structure.signature());
    sampler.load(language_file);
    Sampler::Policy policy(subset, target_item_count);

    while (policy.ok() and sampler.try_insert_random(rng, policy)) {
        POMAGMA_DEBUG(policy.size() << " obs after insertion");
    }
}

void restrict_one (
        BinaryRelation & destin_rel,
        const BinaryRelation & src_rel,
        const Carrier & destin_carrier,
        const std::vector<Ob> & src_to_destin __attribute__((unused)),
        const std::vector<Ob> & destin_to_src)
{
    for (auto iter = destin_carrier.iter(); iter.ok(); iter.next()) {
        Ob destin_lhs = * iter;
        DenseSet destin_set = destin_rel.get_Lx_set(destin_lhs);
        Ob src_lhs = destin_to_src[destin_lhs];
        const DenseSet src_set = src_rel.get_Lx_set(src_lhs);
        for (auto iter = destin_carrier.iter(); iter.ok(); iter.next()) {
            Ob destin_rhs = * iter;
            Ob src_rhs = destin_to_src[destin_rhs];
            if (src_set.contains(src_rhs)) {
                destin_set.insert(destin_rhs);
            }
        }
    }
    destin_rel.update();
}

void restrict_one (
        NullaryFunction & destin_fun,
        const NullaryFunction & src_fun,
        const Carrier & destin_carrier __attribute__((unused)),
        const std::vector<Ob> & src_to_destin,
        const std::vector<Ob> & destin_to_src __attribute__((unused)))
{
    if (Ob src_val = src_fun.find()) {
        if (Ob destin_val = src_to_destin[src_val]) {
            destin_fun.insert(destin_val);
        }
    }
}

void restrict_one (
        InjectiveFunction & destin_fun,
        const InjectiveFunction & src_fun,
        const Carrier & destin_carrier,
        const std::vector<Ob> & src_to_destin,
        const std::vector<Ob> & destin_to_src)
{
    for (auto iter = destin_carrier.iter(); iter.ok(); iter.next()) {
        Ob destin_arg = * iter;
        Ob src_arg = destin_to_src[destin_arg];
        if (Ob src_val = src_fun.find(src_arg)) {
            if (Ob destin_val = src_to_destin[src_val]) {
                destin_fun.insert(destin_arg, destin_val);
            }
        }
    }
}

template<class Function>
void restrict_one (
        Function & destin_fun,
        const Function & src_fun,
        const Carrier & destin_carrier,
        const std::vector<Ob> & src_to_destin,
        const std::vector<Ob> & destin_to_src)
{
    for (auto iter = destin_carrier.iter(); iter.ok(); iter.next()) {
        Ob destin_lhs = * iter;
        Ob src_lhs = destin_to_src[destin_lhs];
        for (auto iter = src_fun.iter_lhs(src_lhs); iter.ok(); iter.next()) {
            Ob src_rhs = * iter;
            if (Function::is_symmetric() and src_rhs < src_lhs) { continue; }
            Ob src_val = src_fun.find(src_lhs, src_rhs);
            if (Ob destin_rhs = src_to_destin[src_rhs]) {
                if (Ob destin_val = src_to_destin[src_val]) {
                    if (Function::is_symmetric() and destin_rhs < destin_lhs) {
                        destin_fun.raw_insert(
                                destin_lhs,
                                destin_rhs,
                                destin_val);
                    } else {
                        destin_fun.raw_insert(
                                destin_lhs,
                                destin_rhs,
                                destin_val);
                    }
                }
            }
        }
    }
}

template<class T>
void restrict_all (
        const std::unordered_map<std::string, T *> & destin_map,
        const std::unordered_map<std::string, T *> & src_map,
        const Carrier & destin_carrier,
        const std::vector<Ob> & src_to_destin,
        const std::vector<Ob> & destin_to_src)
{
    // TODO parallelize
    for (auto pair : destin_map) {
        auto & name = pair.first;
        auto & destin = * pair.second;
        auto i = src_map.find(name);
        if (i == src_map.end()) {
            POMAGMA_WARN("missing " << name);
        } else {
            POMAGMA_INFO("trimming " << name);
            auto & src = * i->second;
            restrict_one(
                    destin,
                    src,
                    destin_carrier,
                    src_to_destin,
                    destin_to_src);
        }
    }
}

void restrict_structure (
        Structure & destin,
        Structure & src,
        const DenseSet & src_subset)
{
    POMAGMA_ASSERT_EQ(destin.carrier().item_count(), 0);

    // build mapping
    // TODO sort intelligently here, or make sure chart is sorted intelligently
    std::vector<Ob> src_to_destin(1 + src.carrier().item_dim(), 0);
    std::vector<Ob> destin_to_src(1 + destin.carrier().item_dim(), 0);
    Ob destin_ob = 1;
    for (auto iter = src_subset.iter(); iter.ok(); iter.next()) {
        Ob src_ob = * iter;
        destin.carrier().raw_insert(destin_ob);
        src_to_destin[src_ob] = destin_ob;
        destin_to_src[destin_ob] = src_ob;
        ++destin_ob;
    }
    destin.carrier().update();

    // copy data
#define POMAGMA_RESTRICT_ALL(arity)\
    detail::restrict_all(\
            destin.signature().arity(),\
            src.signature().arity(),\
            destin.carrier(),\
            src_to_destin,\
            destin_to_src)

    // TODO parallelize
    POMAGMA_RESTRICT_ALL(binary_relations);
    POMAGMA_RESTRICT_ALL(nullary_functions);
    POMAGMA_RESTRICT_ALL(injective_functions);
    POMAGMA_RESTRICT_ALL(binary_functions);
    POMAGMA_RESTRICT_ALL(symmetric_functions);

#undef POMAGMA_RESTRICT_ALL
}

} // namespace detail

void trim (
        Structure & src,
        Structure & destin,
        const char * theory_file,
        const char * language_file)
{
    POMAGMA_INFO("Trimming structure");

    POMAGMA_ASSERT(& destin != & src, "cannot trim structure into self");
    POMAGMA_ASSERT_EQ(destin.carrier().item_count(), 0);
    POMAGMA_ASSERT_LT(destin.carrier().item_dim(), src.carrier().item_count());

    // fill subset
    const size_t destin_item_dim = destin.carrier().item_dim();
    DenseSet src_subset(src.carrier().item_dim());
    detail::insert_nullary_functions(src, src_subset, destin_item_dim);
    detail::assume_core_facts(src, src_subset, destin_item_dim, theory_file);
    detail::fill_random(src, src_subset, destin_item_dim, language_file);
    POMAGMA_ASSERT_EQ(src_subset.count_items(), destin_item_dim);

    // restrict structure
    detail::restrict_structure(destin, src, src_subset);
}

} // namespace pomagma
