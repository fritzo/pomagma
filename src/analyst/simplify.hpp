#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

struct ParsedTerm
{
    Ob ob;
    std::string route;
};

ParsedTerm simplify(
        Structure & structure,
        const std::vector<std::string> & routes,
        const std::string term);

void batch_simplify(
        Structure & structure,
        const std::vector<std::string> & routes,
        const char * source_file,
        const char * destin_file);

} // namespace pomagma
