#pragma once

#include <pomagma/reducer/engine.hpp>
#include <pomagma/reducer/io.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma {
namespace reducer {

class Server {
   public:
    Server();
    ~Server();

    bool validate(std::vector<std::string>& errors);
    std::string reduce(const std::string& code, size_t budget);
    void stop() { serving_ = false; }

    void serve(const char* address);

    std::vector<std::string> flush_errors();

   private:
    reducer::Engine engine_;
    reducer::EngineIO io_;
    std::vector<std::string> error_log_;
    bool serving_;
};

}  // namespace reducer
}  // namespace pomagma
