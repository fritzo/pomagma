#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma {

enum class Trool { kMaybe = 0, kFalse = 1, kTrue = 2 };

inline constexpr Trool and_trool(Trool lhs, Trool rhs) {
    return (lhs == Trool::kFalse or rhs == Trool::kFalse)  ? Trool::kFalse
           : (lhs == Trool::kTrue and rhs == Trool::kTrue) ? Trool::kTrue
                                                           : Trool::kMaybe;
}

static_assert(and_trool(Trool::kMaybe, Trool::kMaybe) == Trool::kMaybe,
              "error");
static_assert(and_trool(Trool::kMaybe, Trool::kFalse) == Trool::kFalse,
              "error");
static_assert(and_trool(Trool::kMaybe, Trool::kTrue) == Trool::kMaybe, "error");
static_assert(and_trool(Trool::kFalse, Trool::kMaybe) == Trool::kFalse,
              "error");
static_assert(and_trool(Trool::kFalse, Trool::kFalse) == Trool::kFalse,
              "error");
static_assert(and_trool(Trool::kFalse, Trool::kTrue) == Trool::kFalse, "error");
static_assert(and_trool(Trool::kTrue, Trool::kMaybe) == Trool::kMaybe, "error");
static_assert(and_trool(Trool::kTrue, Trool::kFalse) == Trool::kFalse, "error");
static_assert(and_trool(Trool::kTrue, Trool::kTrue) == Trool::kTrue, "error");

template <class T>
inline constexpr T case_trool(Trool trool, T if_maybe, T if_false, T if_true) {
    return (trool == Trool::kMaybe)   ? if_maybe
           : (trool == Trool::kFalse) ? if_false
                                      : if_true;
}

}  // namespace pomagma
