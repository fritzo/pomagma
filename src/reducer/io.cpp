#include <pomagma/reducer/io.hpp>

#include <pomagma/reducer/engine.hpp>

#define POMAGMA_LOG_TO(log, message) \
    {                                \
        std::ostringstream o;        \
        o << message;                \
        (log).push_back(o.str());    \
    }

namespace pomagma {
namespace reducer {

EngineIO::EngineIO(Engine& engine)
    : engine_(engine),
      name_to_atom_({
          {"I", Engine::atom_I},
          {"K", Engine::atom_K},
          {"B", Engine::atom_B},
          {"C", Engine::atom_C},
          {"S", Engine::atom_S},
      }),
      atom_to_name_({"", "I", "K", "B", "C", "S"}) {}

Ob EngineIO::parse(const std::string& str, std::vector<std::string>& errors) {
    std::stringstream stream(str);
    std::string token;
    Ob ob = parse(stream, token, errors);
    if (not ob) {
        POMAGMA_ASSERT1(not errors.empty(), "no error was logged");
        return 0;
    }
    if (std::getline(stream, token)) {
        POMAGMA_LOG_TO(errors, "parse error: unexpected token: " << token);
        return 0;
    }
    return ob;
}

Ob EngineIO::parse(std::stringstream& stream, std::string& token,
                   std::vector<std::string>& errors) {
    if (not std::getline(stream, token, ' ')) {
        POMAGMA_LOG_TO(errors, "parse error: early termination");
        return 0;
    }
    if (token == "APP") {
        Ob lhs = parse(stream, token, errors);
        Ob rhs = parse(stream, token, errors);
        if (not(lhs and rhs)) {
            return 0;
        }
        return engine_.app(lhs, rhs);
    }
    const auto i = name_to_atom_.find(token);
    if (i == name_to_atom_.end()) {
        POMAGMA_LOG_TO(errors, "parse error: unrecognized token: " << token);
        return 0;
    }
    return i->second;
}

std::string EngineIO::print(Ob ob) const {
    std::string result;
    append(ob, result);
    return result;
}

void EngineIO::append(Ob ob, std::string& append_str) const {
    static const std::string atoms[] = {"", "I", "K", "B", "C", "S"};
    if (engine_.is_atom(ob)) {
        append_str.append(atoms[ob]);
    } else {
        append_str.append("APP ");
        append(engine_.get_lhs(ob), append_str);
        append_str.append(" ");
        append(engine_.get_rhs(ob), append_str);
    }
}

}  // namespace reducer
}  // namespace pomagma