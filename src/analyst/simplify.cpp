#include "simplify.hpp"

namespace pomagma
{

void batch_simplify(
        Structure & structure,
        const std::vector<std::string> & routes,
        const char * source_file,
        const char * destin_file)
{
    POMAGMA_INFO("simplifying expressions");
    SimplifyParser parser(structure.signature(), routes);

    std::ofstream destin(destin_file);
    POMAGMA_ASSERT(destin, "failed to open " << destin_file);
    destin << "# expressions simplifed by pomagma\n";

    for (LineParser iter(source_file); iter.ok(); iter.next()) {
        const std::string & expression = * iter;
        POMAGMA_DEBUG("simplifying " << expression);

        parser.begin(expression);
        std::string type = parser.parse_token();
        SimplifyTerm lhs = parser.parse_term();
        SimplifyTerm rhs = parser.parse_term();
        parser.end();
        destin << type << " " << lhs.route << " " << rhs.route << "\n";
    }
}

} // namespace pomagma

