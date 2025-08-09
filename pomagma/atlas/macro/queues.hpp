#include <tuple>
#include <vector>

#include "pomagma/atlas/obs.hpp"

namespace pomagma {

class Carrier;

struct BinaryFunctionQueue {
    BinaryFunctionQueue() { clear(); }
    std::vector<std::tuple<Ob, Ob, Ob>> m_tasks;
    void insert(Ob lhs, Ob rhs, Ob val) { m_tasks.emplace_back(lhs, rhs, val); }
    void clear();
    void process_mergers(const Carrier& carrier);
};

}  // namespace pomagma
