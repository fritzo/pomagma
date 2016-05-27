#include <pomagma/reducer/engine.hpp>
#include <pomagma/reducer/io.hpp>
#include <pomagma/util/util.hpp>

using namespace pomagma;
using namespace pomagma::reducer;

int main(int argc, char** argv) {
    std::cout << "Usage: " << argv[0] << " [ARGS]" << std::endl;

    const size_t default_budget = 1000;
    const size_t initial_budget =
        getenv_default("POMAGMA_BUDGET", default_budget);

    Engine engine;
    EngineIO io(engine);

    int returncode = 0;
    for (int i = 1; i < argc; ++i) {
        std::cout << "In: " << argv[i] << std::endl;
        std::vector<std::string> errors;
        if (Ob ob = io.parse(argv[i], errors)) {
            size_t budget = initial_budget;
            Ob red = engine.reduce(ob, budget);
            std::cout << "Out: " << io.print(red) << std::endl;
        }
        for (const std::string& error : errors) {
            std::cout << "Error: " << error << std::endl;
        }
        returncode += errors.size();
    }

    return returncode;
}
