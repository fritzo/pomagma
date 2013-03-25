#include "util.hpp"
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
        POMAGMA_DEBUG("setting P(" << term.name() << ") = " << term.weight());
        set_language_prob(term.name(), term.weight());
    }
}

} // namespace pomagma


inline std::string get_pomagma_root (const std::string & path)
{
    const std::string server = pomagma::get_filename(path);
    size_t pos = server.find_last_of(".");
    const std::string stem(server.begin(), server.begin() + pos);
    const std::string home = getenv("HOME");
    const std::string pomagma_default = home + "/pomagma";
    const std::string pomagma_root = pomagma::getenv_default(
            "POMAGMA_ROOT",
            pomagma_default.c_str());
    return pomagma_root + "/src/language/" + stem + ".language";
}



inline std::string get_name (const std::string & path)
{
    const std::string server = pomagma::get_filename(path);
    size_t pos = server.find_last_of(".");
    return std::string(server.begin(), server.begin() + pos);
}

int main (int argc, char ** argv)
{
    pomagma::Log::title(argc, argv);

    const std::string HOME = getenv("HOME");
    const std::string DEFAULT_ROOT = HOME + "/pomagma";
    const std::string POMAGMA_ROOT = pomagma::getenv_default(
            "POMAGMA_ROOT",
            DEFAULT_ROOT.c_str());
    const std::string STEM = get_name(argv[0]);
    const std::string DEFAULT_THEORY =
        POMAGMA_ROOT + "/src/theory/" + STEM + ".compiled";
    const std::string DEFAULT_LANGUAGE =
        POMAGMA_ROOT + "/src/language/" + STEM + ".language";
    const char * theory_file = pomagma::getenv_default(
            "POMAGMA_THEORY",
            DEFAULT_THEORY.c_str());
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
                << pomagma::get_filename(argv[0])
                << " [structure_in] structure_out" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_ROOT = $HOME/pomagma\n"
            << "  POMAGMA_THEORY = " << DEFAULT_THEORY << "\n"
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
    pomagma::Scheduler::initialize(theory_file);
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
