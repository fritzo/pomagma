#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

class Simplifier
{
    class Reducer;
    class Parser;

public:

    Simplifier (
            Signature & signature,
            const std::vector<std::string> & routes,
            std::vector<std::string> & error_log);
    ~Simplifier ();

    std::string simplify (const std::string & expression);

private:

    Parser & m_parser;
};

} // namespace pomagma
