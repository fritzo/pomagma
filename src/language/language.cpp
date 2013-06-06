#include "language.hpp"
#include "language.pb.h"
#include <pomagma/platform/util.hpp>

namespace pomagma
{

std::unordered_map<std::string, float> load_language (const char * filename)
{
    POMAGMA_INFO("Loading languge");

    messaging::Language language;

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

    return result;
}

} // namespace pomagma
