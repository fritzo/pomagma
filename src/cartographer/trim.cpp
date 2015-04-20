#include "trim.hpp"
#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/macrostructure/sampler.hpp>
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include "collect_parser.hpp"
#include <algorithm>

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
            if (not subset.contains(val)) {
                subset.insert(val);
            }
        }
    }
    POMAGMA_ASSERT_LE(subset.count_items(), target_item_count);
}

void assume_core_facts (
        Structure & structure,
        DenseSet & subset,
        size_t target_item_count,
        const char * theory_file)
{
    CollectParser parser(structure.signature(), subset, target_item_count);
    for (LineParser iter(theory_file); iter.ok(); iter.next()) {
        const std::string & expression = * iter;
        POMAGMA_DEBUG("assume " << expression);

        parser.begin(expression);
        std::string type = parser.parse_token();
        if (type == "EQUAL" or structure.signature().binary_relation(type)) {
            Ob lhs = parser.parse_term();
            Ob rhs = parser.parse_term();
            parser.end();
            if (not (lhs and rhs)) {
                POMAGMA_WARN("failed to assume " << expression);
            }
        } else if (structure.signature().unary_relation(type)) {
            Ob arg = parser.parse_term();
            parser.end();
            if (not arg) {
                POMAGMA_WARN("failed to assume " << expression);
            }
        } else {
            POMAGMA_ERROR("bad relation type: " << type);
        }
    }
}

void fill_random (
        Structure & structure,
        DenseSet & subset,
        size_t target_item_count,
        const char * language_file)
{
    POMAGMA_INFO("filling randomly");
    Sampler sampler(structure.signature(), Sampler::random_seed());
    sampler.load(language_file);
    Sampler::Policy policy(subset, target_item_count);

    while (policy.ok() and sampler.try_insert_random(policy)) {
        POMAGMA_DEBUG(
            policy.size() << " obs after insertion (target = " <<
            target_item_count << " / " <<
            structure.signature().carrier()->item_count() << ")");
    }
}

void fill_optimal (
        Structure & structure,
        DenseSet & subset,
        size_t target_item_count,
        const char * language_file)
{
    POMAGMA_INFO("filling optimally");

    const size_t start_count = subset.count_items();
    const size_t item_count = structure.carrier().item_count();
    POMAGMA_ASSERT_LE(start_count, target_item_count);
    POMAGMA_ASSERT_LE(target_item_count, item_count);
    const size_t add_count = target_item_count - start_count;

    auto language = load_language(language_file);
    Router router(structure.signature(), language);
    std::vector<float> probs = router.measure_probs();
    POMAGMA_ASSERT_EQ(probs.size(), 1 + item_count);

    std::vector<std::pair<float, Ob>> pairs;
    pairs.reserve(item_count);
    for (auto iter = structure.carrier().iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        POMAGMA_ASSERT(ob <= item_count, "structure is not compacted");
        if (not subset.contains(ob)) {
            pairs.push_back(std::make_pair(probs[ob], ob));
        }
    }
    std::sort(pairs.begin(), pairs.end());
    std::reverse(pairs.begin(), pairs.end());
    pairs.resize(add_count);
    for (auto pair : pairs) {
        subset.insert(pair.second);
    }
}

void restrict_one (
        UnaryRelation & destin_rel,
        const UnaryRelation & src_rel,
        const Carrier & destin_carrier,
        const std::vector<Ob> & src_to_destin __attribute__((unused)),
        const std::vector<Ob> & destin_to_src)
{
    for (auto iter = destin_carrier.iter(); iter.ok(); iter.next()) {
        Ob destin_arg = * iter;
        Ob src_arg = destin_to_src[destin_arg];
        if (src_rel.find(src_arg)) {
            destin_rel.insert(destin_arg);
        }
    }
    destin_rel.update();
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
    destin_fun.update();
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
    destin_fun.update();
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
                                destin_rhs,
                                destin_lhs,
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
    destin_fun.update();
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
            POMAGMA_DEBUG("trimming " << name);
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

std::vector<Ob> sort_subset(
        Structure & structure,
        const DenseSet & subset)
{
    POMAGMA_INFO("Sorting subset");

    std::vector<std::pair<long, Ob>> weighted_obs;
    for (auto iter = subset.iter(); iter.ok(); iter.next()) {
        weighted_obs.push_back(std::make_pair<long, Ob>(0, *iter));
    }

    // TODO parallelize
    for (auto pair : structure.signature().binary_relations()) {
        auto rel = pair.second;
        for (auto & weighted_ob : weighted_obs) {
            long & weight = weighted_ob.first;
            Ob & ob = weighted_ob.second;
            weight -= rel->get_Lx_set(ob).count_items();
            weight -= rel->get_Rx_set(ob).count_items();
        }
    }
    for (auto pair : structure.signature().binary_functions()) {
        auto fun = pair.second;
        for (auto & weighted_ob : weighted_obs) {
            long & weight = weighted_ob.first;
            Ob & ob = weighted_ob.second;
            weight -= 16 * fun->get_Lx_set(ob).count_items();
            weight -= 16 * fun->get_Rx_set(ob).count_items();
        }
    }
    for (auto pair : structure.signature().symmetric_functions()) {
        auto fun = pair.second;
        for (auto & weighted_ob : weighted_obs) {
            long & weight = weighted_ob.first;
            Ob & ob = weighted_ob.second;
            weight -= 32 * fun->get_Lx_set(ob).count_items();
        }
    }

    std::sort(weighted_obs.begin(), weighted_obs.end());

    std::vector<Ob> sorted;
    sorted.push_back(0);
    for (auto weighted_ob : weighted_obs) {
        Ob ob = weighted_ob.second;
        sorted.push_back(ob);
    }

    return sorted;
}

void restrict_structure (
        Structure & destin,
        Structure & src,
        const std::vector<Ob> & destin_to_src)
{
    POMAGMA_INFO("Restricting structure");
    POMAGMA_ASSERT_EQ(destin.carrier().item_count(), 0);
    POMAGMA_ASSERT_EQ(
        destin_to_src.size(),
        1 + destin.carrier().item_dim());

    // build mapping
    std::vector<Ob> src_to_destin(1 + src.carrier().item_dim(), 0);
    for (size_t destin_ob = 1; destin_ob < destin_to_src.size(); ++destin_ob) {
        destin.carrier().raw_insert(destin_ob);
        src_to_destin[destin_to_src[destin_ob]] = destin_ob;
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
    POMAGMA_RESTRICT_ALL(unary_relations);
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
        const char * language_file,
        bool temperature)
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
    if (temperature) {
        detail::fill_random(src, src_subset, destin_item_dim, language_file);
    } else {
        detail::fill_optimal(src, src_subset, destin_item_dim, language_file);
    }
    POMAGMA_ASSERT_EQ(src_subset.count_items(), destin_item_dim);

    // restrict structure
    std::vector<Ob> destin_to_src = detail::sort_subset(src, src_subset);
    detail::restrict_structure(destin, src, destin_to_src);
}

} // namespace pomagma
