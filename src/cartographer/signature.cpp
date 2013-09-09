#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/macrostructure/router.hpp>

namespace pomagma
{

void extend (Signature & destin, const Signature & source)
{
    POMAGMA_ASSERT(destin.carrier(), "destin carrier is not initialized");

    auto & carrier = * destin.carrier();

    for (auto i : source.binary_relations()) {
        if (not destin.binary_relations(i.first)) {
            destin.declare(i.first, * new BinaryRelation(carrier));
        }
    }
    for (auto i : source.nullary_functions()) {
        if (not destin.nullary_functions(i.first)) {
            destin.declare(i.first, * new NullaryFunction(carrier));
        }
    }
    for (auto i : source.injective_functions()) {
        if (not destin.injective_functions(i.first)) {
            destin.declare(i.first, * new InjectiveFunction(carrier));
        }
    }
    for (auto i : source.binary_functions()) {
        if (not destin.binary_functions(i.first)) {
            destin.declare(i.first, * new BinaryFunction(carrier));
        }
    }
    for (auto i : source.symmetric_functions()) {
        if (not destin.symmetric_functions(i.first)) {
            destin.declare(i.first, * new SymmetricFunction(carrier));
        }
    }
}

DenseSet restricted (const Signature & destin, const Signature & source)
{
    std::unordered_map<std::string, float> language;
    bool dropped = false;

    for (auto i : destin.nullary_functions()) {
        if (source.nullary_functions(i.first)) {
            language[i.first] = NAN;
        } else {
            dropped = true;
        }
    }
    for (auto i : destin.injective_functions()) {
        if (source.injective_functions(i.first)) {
            language[i.first] = NAN;
        } else {
            dropped = true;
        }
    }
    for (auto i : destin.binary_functions()) {
        if (source.binary_functions(i.first)) {
            language[i.first] = NAN;
        } else {
            dropped = true;
        }
    }
    for (auto i : destin.symmetric_functions()) {
        if (source.symmetric_functions(i.first)) {
            language[i.first] = NAN;
        } else {
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
