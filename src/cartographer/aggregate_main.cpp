#include "aggregate.hpp"
#include <pomagma/macrostructure/carrier.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/macrostructure/compact.hpp>

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * structure_in1 = nullptr;
    const char * structure_in2 = nullptr;
    const char * structure_out = nullptr;

    if (argc == 4) {
        structure_in1 = argv[1];
        structure_in2 = argv[2];
        structure_out = argv[3];
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " larger_in smaller_in aggregate_out"
                << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    // load src
    pomagma::Structure src;
    src.load(structure_in2);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        src.validate();
    }

    // load destin
    pomagma::Structure destin;
    size_t src_item_count = src.carrier().item_count();
    destin.load(structure_in1, src_item_count);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        destin.validate();
    }
    size_t destin_item_count = destin.carrier().item_count();
    if (src_item_count > destin_item_count) {
        POMAGMA_WARN("aggregating larger structure into smaller structure");
    }

    // aggregate
    pomagma::aggregate(destin, src);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        destin.validate();
    }

    // compact
    pomagma::compact(destin);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        destin.validate();
    } else {
        destin.validate_consistent();
    }

    // TODO
    //pomagma::log_stats();

    destin.dump(structure_out);

    return 0;
}
