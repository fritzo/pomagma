#pragma once

#include <pomagma/reducer/engine.hpp>
#include <pomagma/reducer/io.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma {

class Server {
    reducer::Engine m_engine;
    reducer::EngineIO m_io;
    std::vector<std::string> m_error_log;

   public:
    Server();
    ~Server();

    bool validate();
    std::string reduce(const std::string& code, size_t budget);
    void stop();

    void serve(const char* address);

    std::vector<std::string> flush_errors();
};

}  // namespace pomagma
