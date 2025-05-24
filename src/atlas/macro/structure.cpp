// clang-format off
#include "structure_impl.hpp"
// clang-format on

#include <pomagma/atlas/structure_impl.hpp>

namespace pomagma {

void Structure::validate_consistent() {
    pomagma::validate_consistent(m_signature);
}

void Structure::validate() { pomagma::validate(m_signature); }

void Structure::clear() { pomagma::clear(m_signature); }

void Structure::load(const std::string& filename, size_t extra_item_dim) {
    clear();
    pomagma::load(m_signature, filename, extra_item_dim);
}

void Structure::dump(const std::string& filename) {
    pomagma::dump(signature(), filename);
}

void Structure::init_carrier(size_t item_dim) {
    clear();
    m_signature.declare(*new Carrier(item_dim));
}

void Structure::log_stats() { pomagma::log_stats(m_signature); }

void Structure::resize(size_t item_dim) {
    Carrier* carrier = new Carrier(item_dim, *m_signature.carrier());

    for (auto pair : m_signature.unary_relations()) {
        auto* rel = new UnaryRelation(*carrier, std::move(*pair.second));
        delete m_signature.replace(pair.first, *rel);
    }
    for (auto pair : m_signature.binary_relations()) {
        auto* rel = new BinaryRelation(*carrier, std::move(*pair.second));
        delete m_signature.replace(pair.first, *rel);
    }
    for (auto pair : m_signature.nullary_functions()) {
        auto* fun = new NullaryFunction(*carrier, std::move(*pair.second));
        delete m_signature.replace(pair.first, *fun);
    }
    for (auto pair : m_signature.injective_functions()) {
        auto* fun = new InjectiveFunction(*carrier, std::move(*pair.second));
        delete m_signature.replace(pair.first, *fun);
    }
    for (auto pair : m_signature.binary_functions()) {
        auto* fun = new BinaryFunction(*carrier, std::move(*pair.second));
        delete m_signature.replace(pair.first, *fun);
    }
    for (auto pair : m_signature.symmetric_functions()) {
        auto* fun = new SymmetricFunction(*carrier, std::move(*pair.second));
        delete m_signature.replace(pair.first, *fun);
    }

    delete m_signature.replace(*carrier);
}

}  // namespace pomagma
