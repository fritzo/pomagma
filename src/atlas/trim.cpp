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
    POMAGMA_INFO("assume " << expression_str);
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
        Structure & structure __attribute__((unused)),
        DenseSet & subset __attribute__((unused)),
        size_t target_item_count __attribute__((unused)),
        const char * language_file __attribute__((unused)))
{
    TODO("implement random insertion");
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

    // build mapping
    // TODO sort intelligently here, or make sure atlas is sorted intelligently
    std::vector<Ob> src_to_destin(1 + src.carrier().item_dim(), 0);
    std::vector<Ob> destin_to_src(1 + destin.carrier().item_dim(), 0);
    for (auto iter = src_subset.iter(); iter.ok(); iter.next()) {
        Ob src_ob = * iter;
        Ob destin_ob = destin.carrier().unsafe_insert();
        src_to_destin[src_ob] = destin_ob;
        destin_to_src[destin_ob] = src_ob;
    }

    // copy data
    TODO("factor out copy code from atlas");
}

} // namespace pomagma
