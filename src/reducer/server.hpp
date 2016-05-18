#pragma once

#include <pomagma/reducer/engine.hpp>
#include <pomagma/reducer/io.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma {
namespace reducer {

class Server : noncopyable {
   public:
    Server();
    ~Server();

    void stop() { serving_ = false; }
    bool validate(std::vector<std::string>& errors);
    void reset();
    std::string reduce(const std::string& code, size_t budget);

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
