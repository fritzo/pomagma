#include "assume.hpp"
#include "consistency.hpp"
#include "find_parser.hpp"
#include <pomagma/macrostructure/binary_relation.hpp>
#include <pomagma/macrostructure/scheduler.hpp>
#include <pomagma/macrostructure/compact.hpp>
#include <algorithm>

namespace pomagma
{

namespace detail
{

void assume_facts (
        Structure & structure,
        const char * theory_file)
{
    POMAGMA_INFO("assuming core facts");

    for (LineParser iter(theory_file); iter.ok(); iter.next()) {
        const std::string & expression = * iter;
        POMAGMA_DEBUG("assume " << expression);

        FindParser parser(structure.signature());
        parser.begin(expression);
        std::string type = parser.parse_token();
        Ob lhs = parser.parse_term();
        Ob rhs = parser.parse_term();
        parser.end();

        if (type == "EQUAL") {
            structure.carrier().ensure_equal(lhs, rhs);
        } else {
            BinaryRelation & rel = structure.binary_relation(type);
            rel.insert(lhs, rhs);
        }
    }
}

} // namespace detail

size_t assume (
        Structure & structure,
        const char * theory_file)
{
    POMAGMA_INFO("Assuming statements");

    int pre_item_count = structure.carrier().item_count();

    configure_scheduler_to_merge_if_consistent(structure);
    detail::assume_facts(structure, theory_file);
    process_mergers(structure.signature());
    compact(structure);

    int post_item_count = structure.carrier().item_count();
    int merge_count = pre_item_count - post_item_count;
    POMAGMA_INFO("assumption merged " << merge_count << " obs");

    return merge_count;
}

} // namespace pomagma
