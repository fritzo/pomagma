#include "validator.hpp"

namespace pomagma
{

std::vector<Approximator::Validity> Validator::validate (
        const std::vector<Corpus::LineOf<const Corpus::Term *>> & lines,
        Corpus::Linker & linker)
{
    std::vector<Approximator::Validity> result;
    for (const auto & line : lines) {
        auto validity = Approximator::Validity::unknown();
        const HashedApproximation * approx = nullptr;
        for (size_t depth = 0; depth < 10; ++depth) {
            const Corpus::Term * term = linker.approximate(line.body, depth);
            auto old_approx = approx;
            approx = m_cache.find(term);
            if (not approx or approx == old_approx) {
                break;
            }
            validity = m_approximator.is_valid(approx->approx);
            if (not is_ambiguous(validity)) {
                break;
            }
        }
        result.push_back(validity);
    }
    return result;
}

} // namespace pomagma
