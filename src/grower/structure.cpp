#include "structure.hpp"
#include "binary_relation.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include "hdf5.hpp"

namespace pomagma
{

//----------------------------------------------------------------------------
// construction

Structure::Structure (Signature & signature)
    : Signature::Observer(signature),
      m_carrier(signature.carrier())
{
    hdf5::init();
}

void Structure::declare (const std::string & name, BinaryRelation & rel)
{
    m_binary_relations[name] = & rel;
}

void Structure::declare (const std::string & name, NullaryFunction & fun)
{
    m_nullary_functions[name] = & fun;
}

void Structure::declare (const std::string & name, InjectiveFunction & fun)
{
    m_injective_functions[name] = & fun;
}

void Structure::declare (const std::string & name, BinaryFunction & fun)
{
    m_binary_functions[name] = & fun;
}

void Structure::declare (const std::string & name, SymmetricFunction & fun)
{
    m_symmetric_functions[name] = & fun;
}

//----------------------------------------------------------------------------
// clearing

void Structure::clear ()
{
    POMAGMA_INFO("Clearing structure");
    m_carrier.clear();
    for (auto pair : m_binary_relations) { pair.second->clear(); }
    for (auto pair : m_nullary_functions) { pair.second->clear(); }
    for (auto pair : m_injective_functions) { pair.second->clear(); }
    for (auto pair : m_binary_functions) { pair.second->clear(); }
    for (auto pair : m_symmetric_functions) { pair.second->clear(); }
}

//----------------------------------------------------------------------------
// loading

// adapted from
// http://www.hdfgroup.org/HDF5/Tutor/crtfile.html

void Structure::load (const std::string & filename)
{
    if (m_carrier.item_count()) { clear(); }

    POMAGMA_INFO("Loading structure from file " << filename);

    hdf5::InFile file(filename);
    hdf5::Group carrier_group(file, "/carrier");
    hdf5::Group relations_group(file, "/relations");
    hdf5::Group functions_group(file, "/functions");

    // TODO do this in parallel
    // TODO verify SHA1 hash http://www.openssl.org/docs/crypto/sha.html
    load_carrier(file);

    load_binary_relations(file);
    load_nullary_functions(file);
    load_injective_functions(file);
    load_binary_functions(file);
    load_symmetric_functions(file);
}

void Structure::load_carrier (hdf5::InFile & file)
{
    POMAGMA_INFO("loading carrier");

    hdf5::Dataset dataset(file, "/carrier/support");

    hdf5::Dataspace dataspace(dataset);
    const auto shape = dataspace.shape();
    POMAGMA_ASSERT_EQ(shape.size(), 1);
    size_t source_item_dim = shape[0] * BITS_PER_WORD - 1;
    size_t destin_item_dim = m_carrier.item_dim();
    POMAGMA_ASSERT_LE(source_item_dim, destin_item_dim);

    DenseSet support(m_carrier.item_dim());

    dataset.read_all(support);

    for (auto i = support.iter(); i.ok(); i.next()) {
        m_carrier.raw_insert(*i);
    }
    m_carrier.update();
}

void Structure::load_binary_relations (hdf5::InFile & file)
{
    const std::string groupname = "/relations/binary";
    hdf5::Group group(file, groupname);

    // TODO parallelize loop
    for (const auto & pair : m_binary_relations) {
        std::string name = groupname + "/" + pair.first;
        BinaryRelation * rel = pair.second;
        POMAGMA_INFO("loading " << name);

        size_t dim1 = 1 + rel->item_dim();
        size_t dim2 = rel->round_word_dim();
        std::atomic<Word> * destin = rel->raw_data();

        hdf5::Dataset dataset(file, name);
        dataset.read_rectangle(destin, dim1, dim2);
        rel->update();
    }
}

void Structure::load_nullary_functions (hdf5::InFile & file)
{
    const std::string groupname = "/functions/nullary";
    hdf5::Group group(file, groupname);

    for (const auto & pair : m_nullary_functions) {
        std::string name = groupname + "/" + pair.first;
        NullaryFunction * fun = pair.second;
        POMAGMA_INFO("loading " << name);

        hdf5::Group subgroup(file, name);
        hdf5::Dataset dataset(file, name + "/value");

        Ob data;
        dataset.read_scalar(data);
        fun->raw_insert(data);
    }
}

void Structure::load_injective_functions (hdf5::InFile & file)
{
    const size_t item_dim = m_carrier.item_dim();
    std::vector<Ob> data(1 + item_dim);

    const std::string groupname = "/functions/injective";
    hdf5::Group group(file, groupname);

    for (const auto & pair : m_injective_functions) {
        std::string name = groupname + "/" + pair.first;
        InjectiveFunction * fun = pair.second;
        POMAGMA_INFO("loading " << name);

        hdf5::Group subgroup(file, name);
        hdf5::Dataset dataset(file, name + "/value");

        dataset.read_all(data);

        for (Ob key = 1; key <= item_dim; ++key) {
            if (Ob value = data[key]) {
                fun->raw_insert(key, value);
            }
        }
    }
}

namespace detail
{

template<class Function>
inline void load_functions (
        const std::string & arity,
        std::map<std::string, Function *> functions,
        const Carrier & carrier,
        hdf5::InFile & file)

{
    const size_t item_dim = carrier.item_dim();
    typedef uint_<2 * sizeof(Ob)>::t ptr_t;
    std::vector<ptr_t> lhs_ptr_data(1 + item_dim);
    std::vector<Ob> rhs_data(item_dim);
    std::vector<Ob> value_data(item_dim);

    const std::string groupname = "/functions/" + arity;
    hdf5::Group group(file, groupname);

    // TODO parallelize loop
    for (const auto & pair : functions) {
        std::string name = groupname + "/" + pair.first;
        Function * fun = pair.second;
        POMAGMA_INFO("loading " << name);

        hdf5::Group subgroup(file, name);
        hdf5::Dataset lhs_ptr_dataset(file, name + "/lhs_ptr");
        hdf5::Dataset rhs_dataset(file, name + "/rhs");
        hdf5::Dataset value_dataset(file, name + "/value");

        hdf5::Dataspace lhs_ptr_dataspace(lhs_ptr_dataset);
        hdf5::Dataspace rhs_dataspace(rhs_dataset);
        hdf5::Dataspace value_dataspace(value_dataset);

        auto lhs_ptr_shape = lhs_ptr_dataspace.shape();
        POMAGMA_ASSERT_EQ(lhs_ptr_shape.size(), 1);
        POMAGMA_ASSERT_LE(lhs_ptr_shape[0], 1 + item_dim);
        POMAGMA_ASSERT_EQ(rhs_dataspace.shape(), value_dataspace.shape());

        lhs_ptr_dataset.read_all(lhs_ptr_data);
        lhs_ptr_data.push_back(rhs_dataspace.volume());
        for (Ob lhs = 1; lhs < lhs_ptr_data.size() - 1; ++lhs) {
            size_t begin = lhs_ptr_data[lhs];
            size_t end = lhs_ptr_data[lhs + 1];
            POMAGMA_ASSERT_LE(begin, end);
            if (size_t count = end - begin) {

                rhs_data.resize(count);
                rhs_dataset.read_block(rhs_data, begin);

                value_data.resize(count);
                value_dataset.read_block(value_data, begin);

                for (size_t i = 0; i < count; ++i) {
                    fun->raw_insert(lhs, rhs_data[i], value_data[i]);
                }
            }
        }
    }
}

} // namespace detail

void Structure::load_binary_functions (hdf5::InFile & file)
{
    detail::load_functions("binary", m_binary_functions, m_carrier, file);
}

void Structure::load_symmetric_functions (hdf5::InFile & file)
{
    detail::load_functions("symmetric", m_symmetric_functions, m_carrier, file);
}

//----------------------------------------------------------------------------
// dumping

void Structure::dump (const std::string & filename)
{
    POMAGMA_INFO("Dumping structure to file " << filename);
    hdf5::OutFile file(filename);
    hdf5::Group carrier_group(file, "/carrier");
    hdf5::Group relations_group(file, "/relations");
    hdf5::Group functions_group(file, "/functions");

    // TODO do this in parallel
    // TODO compute SHA1 hash http://www.openssl.org/docs/crypto/sha.html
    dump_carrier(file);
    dump_binary_relations(file);
    dump_nullary_functions(file);
    dump_injective_functions(file);
    dump_binary_functions(file);
    dump_symmetric_functions(file);
}

void Structure::dump_carrier (hdf5::OutFile & file)
{
    POMAGMA_INFO("dumping carrier");

    const DenseSet & support = m_carrier.support();

    hdf5::Dataspace dataspace(support.word_dim());

    hdf5::Dataset dataset(
            file,
            "/carrier/support",
            hdf5::Bitfield<Word>::id(),
            dataspace);

    dataset.write_all(support);
}

void Structure::dump_binary_relations (hdf5::OutFile & file)
{
    const DenseSet & support = m_carrier.support();
    const size_t item_dim = support.item_dim();
    const size_t word_dim = support.word_dim();

    hdf5::Dataspace dataspace(1 + item_dim, word_dim);

    const std::string groupname = "/relations/binary";
    hdf5::Group group(file, groupname);

    // TODO parallelize loop
    for (const auto & pair : m_binary_relations) {
        std::string name = groupname + "/" + pair.first;
        const BinaryRelation * rel = pair.second;
        POMAGMA_INFO("dumping " << name);

        hdf5::Dataset dataset(
                file,
                name,
                hdf5::Bitfield<Word>::id(),
                dataspace);

        size_t dim1 = 1 + rel->item_dim();
        size_t dim2 = rel->round_word_dim();
        const std::atomic<Word> * source = rel->raw_data();

        dataset.write_rectangle(source, dim1, dim2);
    }
}

void Structure::dump_nullary_functions (hdf5::OutFile & file)
{
    hdf5::Dataspace dataspace;

    const std::string groupname = "/functions/nullary";
    hdf5::Group group(file, groupname);

    for (const auto & pair : m_nullary_functions) {
        std::string name = groupname + "/" + pair.first;
        const NullaryFunction * fun = pair.second;
        POMAGMA_INFO("dumping " << name);

        hdf5::Group subgroup(file, name);
        hdf5::Dataset dataset(
                file,
                name + "/value",
                hdf5::Unsigned<Ob>::id(),
                dataspace);

        Ob data = fun->find();
        dataset.write_scalar(data);
    }
}

void Structure::dump_injective_functions (hdf5::OutFile & file)
{
    // format:
    // dense array with null entries

    const size_t item_dim = m_carrier.item_dim();
    hdf5::Dataspace dataspace(1 + item_dim);

    const std::string groupname = "/functions/injective";
    hdf5::Group group(file, groupname);

    for (const auto & pair : m_injective_functions) {
        std::string name = groupname + "/" + pair.first;
        const InjectiveFunction * fun = pair.second;
        POMAGMA_INFO("dumping " << name);

        hdf5::Group subgroup(file, name);
        hdf5::Dataset dataset(
                file,
                name + "/value",
                hdf5::Unsigned<Ob>::id(),
                dataspace);

        std::vector<Ob> data(1 + item_dim, 0);
        for (auto key = fun->iter(); key.ok(); key.next()) {
            data[*key] = fun->raw_find(*key);
        }

        dataset.write_all(data);
    }
}

namespace detail
{

template<class Function>
inline void dump_functions (
        const std::string & arity,
        std::map<std::string, Function *> functions,
        const Carrier & carrier,
        hdf5::OutFile & file)
{
    // format:
    // compressed sparse row (CSR) matrix

    const size_t item_dim = carrier.item_dim();

    typedef uint_<2 * sizeof(Ob)>::t ptr_t;
    auto ptr_type = hdf5::Unsigned<ptr_t>::id();
    auto ob_type = hdf5::Unsigned<Ob>::id();

    hdf5::Dataspace ptr_dataspace(1 + item_dim);

    std::vector<ptr_t> lhs_ptr_data(1 + item_dim);
    std::vector<Ob> rhs_data(1 + item_dim);
    std::vector<Ob> value_data(1 + item_dim);

    const std::string groupname = "/functions/" + arity;
    hdf5::Group group(file, groupname);

    // TODO parallelize loop
    for (const auto & pair : functions) {
        std::string name = groupname + "/" + pair.first;
        const Function * fun = pair.second;
        POMAGMA_INFO("dumping " << name);

        size_t pair_count = fun->count_pairs();
        POMAGMA_DEBUG("dumping " << pair_count << " lhs,rhs pairs");
        hdf5::Dataspace ob_dataspace(pair_count);

        hdf5::Group subgroup(file, name);
        hdf5::Dataset lhs_ptr_dataset(
                file,
                name + "/lhs_ptr",
                ptr_type,
                ptr_dataspace);
        hdf5::Dataset rhs_dataset(
                file,
                name + "/rhs",
                ob_type,
                ob_dataspace);
        hdf5::Dataset value_dataset(
                file,
                name + "/value",
                ob_type,
                ob_dataspace);

        ptr_t pos = 0;
        lhs_ptr_data[0] = pos;
        for (Ob lhs = 1; lhs <= item_dim; ++lhs) {
            lhs_ptr_data[lhs] = pos;
            if (carrier.contains(lhs)) {
                rhs_data.clear();
                value_data.clear();
                for (auto rhs = fun->iter_lhs(lhs); rhs.ok(); rhs.next()) {
                    if (Function::is_symmetric() and *rhs > lhs) { break; }
                    rhs_data.push_back(*rhs);
                    value_data.push_back(fun->raw_find(lhs, *rhs));
                }
                if (size_t count = rhs_data.size()) {
                    ptr_t nextpos = pos + count;
                    POMAGMA_ASSERT_LE(nextpos, pair_count);
                    rhs_dataset.write_block(rhs_data, pos);
                    value_dataset.write_block(value_data, pos);
                    pos = nextpos;
                }
            }
        }
        POMAGMA_ASSERT_EQ(pos, pair_count);
        lhs_ptr_dataset.write_all(lhs_ptr_data);
    }
}

} // namespace detail

void Structure::dump_binary_functions (hdf5::OutFile & file)
{
    detail::dump_functions("binary", m_binary_functions, m_carrier, file);
}

void Structure::dump_symmetric_functions (hdf5::OutFile & file)
{
    detail::dump_functions("symmetric", m_symmetric_functions, m_carrier, file);
}

} // namespace pomagma
