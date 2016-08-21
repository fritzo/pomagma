#include <pomagma/reducer/code.hpp>

namespace pomagma {
namespace reducer {

void assert_code(const Code& code) {
    switch (code.type) {
        case Code::APP: {
            POMAGMA_ASSERT(not code.has_rank());
            POMAGMA_ASSERT(not code.has_name());
            POMAGMA_ASSERT_EQ(code.args_size(), 2);
        } break;

        // TODO validate other types

        default:
            break;
    }
}

}  // namespace reducer
}  // namespace pomagma
