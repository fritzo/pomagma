#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/macrostructure/router.hpp>

namespace pomagma
{

void extend (Signature & destin, const Signature & source)
{
    POMAGMA_ASSERT(destin.carrier(), "destin carrier is not initialized");

    auto & carrier = * destin.carrier();

    for (auto i : source.unary_relations()) {
        if (not destin.unary_relation(i.first)) {
            POMAGMA_DEBUG("adding " << i.first);
            destin.declare(i.first, * new UnaryRelation(carrier));
        }
    }
    for (auto i : source.binary_relations()) {
        if (not destin.binary_relation(i.first)) {
            POMAGMA_DEBUG("adding " << i.first);
            destin.declare(i.first, * new BinaryRelation(carrier));
        }
    }
    for (auto i : source.nullary_functions()) {
        if (not destin.nullary_function(i.first)) {
            POMAGMA_DEBUG("adding " << i.first);
            destin.declare(i.first, * new NullaryFunction(carrier));
        }
    }
    for (auto i : source.injective_functions()) {
        if (not destin.injective_function(i.first)) {
            POMAGMA_DEBUG("adding " << i.first);
            destin.declare(i.first, * new InjectiveFunction(carrier));
        }
    }
    for (auto i : source.binary_functions()) {
        if (not destin.binary_function(i.first)) {
            POMAGMA_DEBUG("adding " << i.first);
            destin.declare(i.first, * new BinaryFunction(carrier));
        }
    }
    for (auto i : source.symmetric_functions()) {
        if (not destin.symmetric_function(i.first)) {
            POMAGMA_DEBUG("adding " << i.first);
            destin.declare(i.first, * new SymmetricFunction(carrier));
        }
    }
}

DenseSet restricted (const Signature & destin, const Signature & source)
{
    std::unordered_map<std::string, float> language;
    bool dropped = false;

    for (auto i : destin.nullary_functions()) {
        if (source.nullary_function(i.first)) {
            language[i.first] = NAN;
        } else {
            POMAGMA_INFO("dropping " << i.first);
            dropped = true;
        }
    }
    for (auto i : destin.injective_functions()) {
        if (source.injective_function(i.first)) {
            language[i.first] = NAN;
        } else {
            POMAGMA_INFO("dropping " << i.first);
            dropped = true;
        }
    }
    for (auto i : destin.binary_functions()) {
        if (source.binary_function(i.first)) {
            language[i.first] = NAN;
        } else {
            POMAGMA_INFO("dropping " << i.first);
            dropped = true;
        }
    }
    for (auto i : destin.symmetric_functions()) {
        if (source.symmetric_function(i.first)) {
            language[i.first] = NAN;
        } else {
            POMAGMA_INFO("dropping " << i.first);
            dropped = true;
        }
    }

    DenseSet defined(destin.carrier()->item_dim());
    if (dropped) {
        defined = Router(destin, language).find_defined();
    } else {
        defined = destin.carrier()->support();
    }
    return defined;
}

} // namespace pomagma
