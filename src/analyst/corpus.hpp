#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/analyst/approximate.hpp>
#include <atomic>

namespace pomagma
{

class CorpusApproximation
{
public:

    CorpusApproximation ();
    ~CorpusApproximation ();

    struct Line
    {
        std::string maybe_name;
        std::string code;
    };
    std::vector<Approximator::Validity> validate (
            const std::vector<Line> & lines);

private:

    class Guts;
    Guts * m_guts;
};

} // namespace pomagma
