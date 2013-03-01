#include <pomagma/util/check_structure.hpp>
#include <pomagma/util/signature.hpp>
#include <pomagma/util/hdf5.hpp>
#include <pomagma/util/sequential_dense_set.hpp>
#include <algorithm>

namespace pomagma
{

using namespace sequential;

static void check_file (hdf5::InFile & file)
{
    POMAGMA_DEBUG("checking file");

    auto digest = hdf5::get_tree_hash(file);
    POMAGMA_ASSERT(digest == hdf5::load_hash(file), "file is corrupt");
}

static void check_signature (hdf5::InFile & file, const Signature & signature)
{
    POMAGMA_DEBUG("checking signature");

    Hasher::Dict dict;
    {
        std::string name = "carrier";
        dict[name] = hdf5::load_hash(hdf5::Group(file, name));
    }
    {
        hdf5::Group group(file, "relations");
        {
            hdf5::Group group(file, "relations/binary");
            for (const auto & i : signature.binary_relations()) {
                std::string name = "relations/binary/" + i.first;
                dict[name] = hdf5::load_hash(hdf5::Group(file, name));
            }
        }
    }
    {
        hdf5::Group group(file, "functions");
        {
            hdf5::Group group(file, "functions/nullary");
            for (const auto & i : signature.nullary_functions()) {
                std::string name = "functions/nullary/" + i.first;
                dict[name] = hdf5::load_hash(hdf5::Group(file, name));
            }
        }
        {
            hdf5::Group group(file, "functions/injective");
            for (const auto & i : signature.injective_functions()) {
                std::string name = "functions/injective/" + i.first;
                dict[name] = hdf5::load_hash(hdf5::Group(file, name));
            }
        }
        {
            hdf5::Group group(file, "functions/binary");
            for (const auto & i : signature.binary_functions()) {
                std::string name = "functions/binary/" + i.first;
                dict[name] = hdf5::load_hash(hdf5::Group(file, name));
            }
        }
        {
            hdf5::Group group(file, "functions/symmetric");
            for (const auto & i : signature.symmetric_functions()) {
                std::string name = "functions/symmetric/" + i.first;
                dict[name] = hdf5::load_hash(hdf5::Group(file, name));
            }
        }
    }

    auto hash = Hasher::digest(dict);
    POMAGMA_ASSERT(hash == hdf5::load_hash(file),
            "file does not match signature");
}

static void check_carrier (hdf5::InFile & file)
{
    POMAGMA_DEBUG("checking carrier");

    const std::string groupname = "carrier";
    hdf5::Group group(file, groupname);
    hdf5::Dataset dataset(file, groupname + "/support");

    hdf5::Dataspace dataspace(dataset);
    const auto shape = dataspace.shape();
    POMAGMA_ASSERT_EQ(shape.size(), 1);
    size_t item_dim = shape[0] * BITS_PER_WORD - 1;

    DenseSet support(item_dim);
    dataset.read_set(support);

    Hasher hasher;
    for (auto i = support.iter(); i.ok(); i.next()) {
        uint32_t data = *i;
        hasher.add(data);
    }
    auto hash = hasher.finish();
    POMAGMA_ASSERT(hash == hdf5::load_hash(group),
            groupname << " is corrupt");
}

static void check_binary_relations (hdf5::InFile & file __attribute__((unused)))
{
    POMAGMA_DEBUG("TODO check binary_relations");
}

static void check_nullary_functions (hdf5::InFile & file __attribute__((unused)))
{
    POMAGMA_DEBUG("TODO check nullary_functions");
}

static void check_injective_functions (hdf5::InFile & file __attribute__((unused)))
{
    POMAGMA_DEBUG("TODO check injective_functions");
}

static void check_binary_functions (hdf5::InFile & file __attribute__((unused)))
{
    POMAGMA_DEBUG("TODO check binary_functions");
}

namespace
{

struct Triple
{
    uint32_t lhs;
    uint32_t rhs;
    uint32_t val;
};

inline bool operator< (const Triple & x, const Triple & y)
{
    return unlikely(x.lhs == y.lhs) ? x.rhs < y.rhs : x.lhs < y.lhs;
}

} // anonymous namespace

static void check_symmetric_functions (hdf5::InFile & file __attribute__((unused)))
{
    POMAGMA_DEBUG("TODO check symmetric_functions");

    std::vector<Triple> triples;

    // TODO load ordered triples

    std::sort(triples.begin(), triples.end());
    Hasher hasher;
    for (auto & i : triples) {
        hasher.add_raw(& i, sizeof(Triple));
    }
    //auto hash = hasher.finish();
    //POMAGMA_ASSERT(hash == hdf5::load_hash(group),
    //        groupname << " is corrupt");
}

void check_structure (hdf5::InFile & file, const Signature & signature)
{
    POMAGMA_INFO("Checking structure");

    check_file(file);
    check_signature(file, signature);
    hdf5::Group relations_group(file, "/relations");
    hdf5::Group functions_group(file, "/functions");

    // TODO parallelize
    check_carrier(file);
    check_binary_relations(file);
    check_nullary_functions(file);
    check_injective_functions(file);
    check_binary_functions(file);
    check_symmetric_functions(file);
}

} // namespace pomagma
