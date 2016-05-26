#pragma once

#include <sstream>

#define POMAGMA_LOG_TO(log, message) \
    {                                \
        std::ostringstream o;        \
        o << message;                \
        (log).push_back(o.str());    \
    }
