#include "util.hpp"
#include "carrier.hpp"
#include "structure.hpp"
#include "trim.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::title(argc, argv);

    const char * atlas_in = nullptr;
    const char * chart_out = nullptr;
    const char * theory_file = nullptr;
    const char * language_file = nullptr;
    size_t size_out = 0;

    if (argc == 6) {
        atlas_in = argv[1];
        chart_out = argv[2];
        theory_file = argv[3];
        language_file = argv[4];
        size_out = atoi(argv[5]);
        POMAGMA_ASSERT_LT(0, size_out);
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " atlas_in chart_out theory language size" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    // load src
    pomagma::Structure src;
    src.load(atlas_in);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        src.validate();
    }

    // init destin
    pomagma::Structure destin;
    TODO("copy signature from src to destin, with size_out");
    if (POMAGMA_DEBUG_LEVEL > 1) {
        destin.validate();
    }

    // trim
    pomagma::trim(src, destin, theory_file, language_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        destin.validate();
    }

    // TODO
    //pomagma::log_stats();

    destin.dump(chart_out);

    return 0;
}
