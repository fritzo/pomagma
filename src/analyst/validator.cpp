#include "validator.hpp"

namespace pomagma
{

//----------------------------------------------------------------------------
// Linker

class Validator::Linker
{
public:

    Linker (Validator * v) : m_validator(* v) {}

    void define (const std::string & name, const Corpus::Term * term)
    {
        m_definitions.insert(std::make_pair(name, term));
    }

    const Corpus::Term * link (const Corpus::Term * term)
    {
        TODO("link term");
        return term;
    }

private:

    Validator & m_validator;
    std::unordered_map<std::string, const Corpus::Term *> m_definitions;
};

//----------------------------------------------------------------------------
// Validator

std::vector<Approximator::Validity> Validator::validate (
        const std::vector<Corpus::LineOf<const Corpus::Term *>> & lines)
{
    Linker linker(this);
    for (const auto & line : lines) {
        if (line.is_definition()) {
            linker.define(line.maybe_name, line.body);
        }
    }
    std::vector<Approximator::Validity> result;
    for (const auto & line : lines) {
        const Corpus::Term * term = linker.link(line.body);
        result.push_back(is_valid(term));
    }
    return result;
}

} // namespace pomagma
