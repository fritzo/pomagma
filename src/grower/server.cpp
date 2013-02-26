#include <pomagma/grower/util.hpp>
#include "scheduler.hpp"
#include "language.pb.h"
#include "structure.pb.h"

namespace pomagma
{

void load_structure (const std::string & filename);
void dump_structure (const std::string & filename);
void set_language_prob (const std::string & name, float prob);
void validate_all ();
void log_stats ();

void load_language (const char * filename)
{
    POMAGMA_INFO("Loading language");

    messaging::Language language;

    std::ifstream file(filename, std::ios::in | std::ios::binary);
    POMAGMA_ASSERT(file.is_open(),
        "failed to open language file " << filename);
    POMAGMA_ASSERT(language.ParseFromIstream(&file),
        "failed tp parse language file " << filename);

    for (int i = 0; i < language.terms_size(); ++i) {
        const auto & term = language.terms(i);
        set_language_prob(term.name(), term.weight());
    }
}

} // namespace pomagma


inline std::string get_filename (const std::string & path)
{
    size_t pos = path.find_last_of("/");
    if (pos != std::string::npos) {
        return std::string(path.begin() + pos + 1, path.end());
    } else {
        return path;
    }
}

inline std::string get_language (const std::string & path)
{
    const std::string server = get_filename(path);
    size_t pos = server.find_last_of(".");
    const std::string stem(server.begin(), server.begin() + pos);
    const std::string home = getenv("HOME");
    const std::string pomagma_default = home + "/pomagma";
    const std::string pomagma_root = pomagma::getenv_default(
            "POMAGMA_ROOT",
            pomagma_default.c_str());
    return pomagma_root + "/src/language/" + stem + ".language";
}

int main (int argc, char ** argv)
{
    const std::string DEFAULT_LANGUAGE = get_language(argv[0]);
    const char * language_file = pomagma::getenv_default(
            "POMAGMA_LANGUAGE",
            DEFAULT_LANGUAGE.c_str());
    const size_t thread_count = pomagma::getenv_default(
            "POMAGMA_THREADS",
            pomagma::DEFAULT_THREAD_COUNT);
    const char * structure_in = nullptr;
    const char * structure_out = nullptr;

    if (argc == 2) {
        structure_out = argv[1];
    } else if (argc == 3) {
        structure_in = argv[1];
        structure_out = argv[2];
    } else {
        std::cout
            << "Usage: "
                << get_filename(argv[0])
                << " [structure_in] structure_out" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_ROOT = $HOME/pomagma\n"
            << "  POMAGMA_LANGUAGE = " << DEFAULT_LANGUAGE << "\n"
            << "  POMAGMA_SIZE = " << pomagma::DEFAULT_ITEM_DIM << "\n"
            << "  POMAGMA_THREADS = "
                << pomagma::DEFAULT_THREAD_COUNT << "\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    // set params
    pomagma::Scheduler::set_thread_count(thread_count);
    pomagma::load_language(language_file);
    if (structure_in) {
        pomagma::load_structure(structure_in);
    }
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    }

    // initialize
    if (structure_in) {
        pomagma::cleanup_tasks_push_all();
    }
    pomagma::Scheduler::initialize();
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    }

    // grow
    pomagma::Scheduler::grow();
    if (POMAGMA_DEBUG_LEVEL > 0) {
        pomagma::validate_all();
    }

    pomagma::log_stats();

    pomagma::dump_structure(structure_out);

    return 0;
}
