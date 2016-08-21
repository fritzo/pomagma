#pragma once

#include <pomagma/src/reducer/code.pb.h>
#include <pomagma/src/util/unique_set.hpp>
#include <pomagma/src/util/util.hpp>
#include <pomagma/third_party/farmhash/farmhash.h>

namespace pomagma {
namespace reducer {

void assert_code(const Code& code);

struct Code {
};

class CodeBuilder : noncopyable {
   public:
    const Code* app(const Code* lhs, const Code* rhs);
    const Code* join(const std::vector<Code*> terms);
    const Code* quote(const Code* arg);

    const Code* ivar(const uint32_t rank);
    const Code* abs(const Code* body);

    const Code* nvar(const std::string& name);
    const Code* fun(const std::string& name, const Code* body);
    const Code* let(const std::string& name, const Code* defn,
                    const Code* body);

    const Code* atom_I();

   private:
    UniqueSet<Code, HashCode> codes_;
};

}  // namespace reducer
}  // namespace pomagma
