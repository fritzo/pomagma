#pragma once

#include <cstdlib>
#include <iostream>
#include <pomagma/reducer/obs.hpp>
#include <pomagma/util/util.hpp>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace pomagma {
namespace reducer {

class Engine;

// EngineIO is thread-safe iff Engine is thread-safe.
class EngineIO {
   public:
    EngineIO(Engine& engine);

    // parse() returns 0 on error, and logs errors.
    // parse() may partially reduce the term; print(parse(x)) may differ from x.
    Ob parse(const std::string& str, std::vector<std::string>& errors);
    std::string print(Ob ob) const;

   private:
    Ob parse(std::stringstream& stream, std::string& token,
             std::vector<std::string>& errors);
    void append(Ob ob, std::string& append_str) const;

    Engine& engine_;
    std::unordered_map<std::string, Ob> name_to_atom_;
    const std::vector<std::string> atom_to_name_;
};

}  // namespace reducer
}  // namespace pomagma
