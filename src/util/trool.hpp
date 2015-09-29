#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma {

enum class Trool { MAYBE, FALSE, TRUE };

inline constexpr Trool and_trool (Trool lhs, Trool rhs)
{
    return
        (lhs == Trool::FALSE or rhs == Trool::FALSE) ? Trool::FALSE :
        (lhs == Trool::TRUE and rhs == Trool::TRUE) ? Trool::TRUE :
        Trool::MAYBE;
}

static_assert(and_trool(Trool::MAYBE, Trool::MAYBE) == Trool::MAYBE, "error");
static_assert(and_trool(Trool::MAYBE, Trool::FALSE) == Trool::FALSE, "error");
static_assert(and_trool(Trool::MAYBE, Trool::TRUE) == Trool::MAYBE, "error");
static_assert(and_trool(Trool::FALSE, Trool::MAYBE) == Trool::FALSE, "error");
static_assert(and_trool(Trool::FALSE, Trool::FALSE) == Trool::FALSE, "error");
static_assert(and_trool(Trool::FALSE, Trool::TRUE) == Trool::FALSE, "error");
static_assert(and_trool(Trool::TRUE, Trool::MAYBE) == Trool::MAYBE, "error");
static_assert(and_trool(Trool::TRUE, Trool::FALSE) == Trool::FALSE, "error");
static_assert(and_trool(Trool::TRUE, Trool::TRUE) == Trool::TRUE, "error");

template<class T>
inline constexpr T case_trool (Trool trool, T if_maybe, T if_false, T if_true)
{
    switch (trool) {
        case Trool::MAYBE: return if_maybe;
        case Trool::FALSE: return if_false;
        case Trool::TRUE: return if_true;
    }
}

} // namespace pomagma
