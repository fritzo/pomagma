#include "validator.hpp"

namespace pomagma {

std::vector<Validator::AsyncValidity> Validator::validate(
    const std::vector<Corpus::LineOf<const Corpus::Term *>> &lines,
    Corpus::Linker &linker) {
    std::vector<AsyncValidity> result;
    for (const auto &line : lines) {
        AsyncValidity pair = {Approximator::Validity::unknown(), false};
        const HashedApproximation *approx = nullptr;
        for (size_t depth = 0; depth < 10; ++depth) {
            const Corpus::Term *term = linker.approximate(line.body, depth);
            auto old_approx = approx;
            approx = m_cache.find(term);
            if (not approx) {
                pair.pending = true;
                break;
            }
            if (approx == old_approx) {
                break;
            }
            pair.validity = m_approximator.is_valid(approx->approx);
            if (not is_ambiguous(pair.validity)) {
                break;
            }
        }
        result.push_back(pair);
    }
    return result;
}

}  // namespace pomagma
