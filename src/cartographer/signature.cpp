#include <pomagma/macrostructure/structure_impl.hpp>

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

} // namespace pomagma
