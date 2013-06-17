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

void assume_fact (
        Structure & structure,
        FindParser & parser,
        const std::string & expression_str)
{
    POMAGMA_DEBUG("assume " << expression_str);
    std::istringstream expression(expression_str);

    std::string type;
    POMAGMA_ASSERT(getline(expression, type, ' '), "bad line: " << expression);
    Ob lhs = parser.parse(expression);
    Ob rhs = parser.parse(expression);
    POMAGMA_ASSERT(expression.eof(), "unexpected tokens in " << expression);
    POMAGMA_ASSERT(lhs and rhs, "parse_insert failed");

    if (type == "EQUAL") {
        structure.carrier().ensure_equal(lhs, rhs);
    } else {
        BinaryRelation & rel = structure.binary_relation(type);
        rel.insert(lhs, rhs);
    }
}

void assume_facts (
        Structure & structure,
        const char * theory_file)
{
    POMAGMA_INFO("assuming core facts");
    std::ifstream file(theory_file);
    POMAGMA_ASSERT(file, "failed to open " << theory_file);

    FindParser parser(structure.signature());
    std::string expression;
    while (getline(file, expression)) {
        if (not expression.empty() and expression[0] != '#') {
            assume_fact(structure, parser, expression);
        }
    }
}

} // namespace detail

void assume (
        Structure & structure,
        const char * theory_file)
{
    POMAGMA_INFO("Assuming statements");

    configure_scheduler_to_merge_if_consistent(structure);
    detail::assume_facts(structure, theory_file);
    process_mergers(structure.signature());
    compact(structure);
}

} // namespace pomagma
