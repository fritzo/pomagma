#include "language.hpp"
#include "language.pb.h"
#include <pomagma/util/util.hpp>

namespace pomagma
{

std::unordered_map<std::string, float> load_language (const char * filename)
{
    POMAGMA_INFO("Loading languge");

    protobuf::Language language;

    std::ifstream file(filename, std::ios::in | std::ios::binary);
    POMAGMA_ASSERT(file.is_open(),
        "failed to open language file " << filename);
    POMAGMA_ASSERT(language.ParseFromIstream(&file),
        "failed to parse language file " << filename);

    std::unordered_map<std::string, float> result;
    for (int i = 0; i < language.terms_size(); ++i) {
        const auto & term = language.terms(i);
        POMAGMA_DEBUG("setting P(" << term.name() << ") = " << term.weight());
        result[term.name()] = term.weight();
    }

    float total = 0;
    for (auto & pair : result) {
        total += pair.second;
    }
    float error = fabs(total - 1);
    POMAGMA_ASSERT(error < 1e-4, "language not normalized, total = " << total)
    for (auto & pair : result) {
        pair.second /= total;
    }

    return result;
}

} // namespace pomagma
