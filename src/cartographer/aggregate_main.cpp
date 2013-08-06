#include "aggregate.hpp"
#include "signature.hpp"
#include <pomagma/macrostructure/carrier.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/macrostructure/compact.hpp>

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 4) {
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

    const char * structure_in1 = argv[1];
    const char * structure_in2 = argv[2];
    const char * structure_out = argv[3];

    // load source
    pomagma::Structure source;
    source.load(structure_in2);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        source.validate();
    }

    // load destin
    pomagma::Structure destin;
    size_t source_item_count = source.carrier().item_count();
    destin.load(structure_in1, source_item_count);
    extend(destin.signature(), source.signature());
    if (POMAGMA_DEBUG_LEVEL > 1) {
        destin.validate();
    }
    size_t destin_item_count = destin.carrier().item_count();
    if (source_item_count > destin_item_count) {
        POMAGMA_WARN("aggregating larger structure into smaller structure");
    }

    // aggregate
    pomagma::aggregate(destin, source);
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

    destin.log_stats();
    destin.dump(structure_out);

    return 0;
}
