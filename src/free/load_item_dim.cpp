#include <pomagma/util/util.hpp>
#include <pomagma/util/hdf5.hpp>

using namespace pomagma;
using namespace hdf5;

int main (int argc, char ** argv)
{
    if (argc != 2) {
        std::cerr << "Usage: load_item_dim FILENAME" << std::flush;
        return 1;
    }

    init();
    std::string filename = argv[1];
    InFile file(filename);
    Group group(file, "carrier");
    Dataset dataset(file, "carrier/support");
    hid_t source_type = dataset.type();
    hid_t destin_type = Bitfield<Word>::id();
    POMAGMA_ASSERT(H5Tequal(source_type, destin_type), "datatype mismatch");
    Dataspace dataspace(dataset);
    const auto shape = dataspace.shape();
    POMAGMA_ASSERT_EQ(shape.size(), 1);
    size_t item_dim = shape[0] * BITS_PER_WORD - 1;
    std::cout << item_dim << std::flush;
    return 0;
}
