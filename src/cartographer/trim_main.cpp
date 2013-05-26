#include "util.hpp"
#include "carrier.hpp"
#include "structure.hpp"
#include "trim.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * source_file = nullptr;
    const char * destin_file = nullptr;
    size_t destin_item_dim = 0;
    const char * laws_file = nullptr;
    const char * language_file = nullptr;

    if (argc == 6) {
        source_file = argv[1];
        destin_file = argv[2];
        destin_item_dim = atoi(argv[3]);
        laws_file = argv[4];
        language_file = argv[5];
        POMAGMA_ASSERT_LT(0, destin_item_dim);
        POMAGMA_ASSERT_NE(std::string(source_file), std::string(destin_file));
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " source destin size laws language" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    // load source
    pomagma::Structure source;
    source.load(source_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        source.validate();
    }

    if (source.carrier().item_dim() <= destin_item_dim) {

        source.dump(destin_file);

    } else {

        // init destin
        pomagma::Structure destin;
        destin.init_signature(source, destin_item_dim);
        if (POMAGMA_DEBUG_LEVEL > 1) {
            destin.validate();
        }

        // trim
        pomagma::trim(source, destin, laws_file, language_file);
        if (POMAGMA_DEBUG_LEVEL > 1) {
            destin.validate();
        }

        destin.dump(destin_file);
    }

    // TODO
    //pomagma::log_stats();

    return 0;
}
