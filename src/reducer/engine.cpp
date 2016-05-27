#include <pomagma/reducer/engine.hpp>
#include <pomagma/reducer/util.hpp>

namespace pomagma {
namespace reducer {

Engine::Engine() { reset(); }

Engine::~Engine() {
    POMAGMA_INFO("Engine ob count = " << rep_table_.size());
    POMAGMA_INFO("Engine app count = " << LRv_table_.size());
    if (POMAGMA_DEBUG_LEVEL) {
        assert_valid();
    }
}

#define POMAGMA_VALIDATE_EQ(x, y)                                       \
    {                                                                   \
        if (unlikely((x) != (y))) {                                     \
            valid = false;                                              \
            POMAGMA_LOG_TO(errors, "Expected " #x " == " #y ", actual " \
                                       << (x) << " vs " << (y));        \
        }                                                               \
    }

bool Engine::validate(std::vector<std::string>& errors) const {
    errors.push_back("TODO Validate all terms are linear normal forms.");
    bool valid = true;
    const size_t LRv_count = LRv_table_.size();

    // Validate that Lrv_table_ matches LRv_table_.
    size_t Lrv_count = 0;
    for (const auto& Lrv : Lrv_table_) {
        const Ob lhs = Lrv.first;
        for (const auto& rv : Lrv.second) {
            const Ob rhs = rv.first;
            const Ob val = rv.second;
            auto i = LRv_table_.find({lhs, rhs});
            if (unlikely(i == LRv_table_.end())) {
                valid = false;
                POMAGMA_LOG_TO(errors,
                               "(" << lhs << "," << rhs << "," << val
                                   << ") in Lrv_table_ but not LRv_table_");
                continue;
            }
            ++Lrv_count;
            if (unlikely(i->second != val)) {
                valid = false;
                POMAGMA_LOG_TO(errors, "(" << lhs << "," << rhs << "," << val
                                           << ") in Lrv_table_ but (" << lhs
                                           << "," << rhs << "," << i->second
                                           << ") in LRv_table_");
            }
        }
    }
    POMAGMA_VALIDATE_EQ(Lrv_count, LRv_count);

    // Validate that Rlv_table_ matches LRv_table_.
    size_t Rlv_count = 0;
    for (const auto& Rlv : Rlv_table_) {
        const Ob rhs = Rlv.first;
        for (const auto& lv : Rlv.second) {
            const Ob lhs = lv.first;
            const Ob val = lv.second;
            auto i = LRv_table_.find({lhs, rhs});
            if (unlikely(i == LRv_table_.end())) {
                valid = false;
                POMAGMA_LOG_TO(errors,
                               "(" << lhs << "," << rhs << "," << val
                                   << ") in Rlv_table_ but not LRv_table_");
                continue;
            }
            ++Rlv_count;
            if (unlikely(i->second != val)) {
                valid = false;
                POMAGMA_LOG_TO(errors, "(" << lhs << "," << rhs << "," << val
                                           << ") in Rlv_table_ but (" << lhs
                                           << "," << rhs << "," << i->second
                                           << ") in LRv_table_");
            }
        }
    }
    POMAGMA_VALIDATE_EQ(Rlv_count, LRv_count);

    // Validate that Vlr_table_ matches LRv_table_.
    size_t Vlr_count = 0;
    for (const auto& Vlr : Vlr_table_) {
        const Ob val = Vlr.first;
        for (const auto& lr : Vlr.second) {
            const Ob lhs = lr.first;
            const Ob rhs = lr.second;
            auto i = LRv_table_.find({lhs, rhs});
            if (unlikely(i == LRv_table_.end())) {
                valid = false;
                POMAGMA_LOG_TO(errors,
                               "(" << lhs << "," << rhs << "," << val
                                   << ") in Vlr_table_ but not LRv_table_");
                continue;
            }
            ++Vlr_count;
            if (unlikely(i->second != val)) {
                valid = false;
                POMAGMA_LOG_TO(errors, "(" << lhs << "," << rhs << "," << val
                                           << ") in Vlr_table_ but (" << lhs
                                           << "," << rhs << "," << i->second
                                           << ") in LRv_table_");
            }
        }
    }
    POMAGMA_VALIDATE_EQ(Vlr_count, LRv_count);

    return valid;
}

void Engine::assert_valid() const {
    std::vector<std::string> errors;
    if (validate(errors)) return;
    for (const std::string& error : errors) {
        POMAGMA_WARN(error);
    }
    POMAGMA_ERROR("Engine is invalid");
}

void Engine::reset() {
    // Clear data.
    POMAGMA_ASSERT(merge_queue_.empty(), "tried to reset() while merging");
    LRv_table_.clear();
    Lrv_table_.clear();
    Rlv_table_.clear();
    Vlr_table_.clear();
    rep_table_.clear();

    // Initialize atoms to be reduced.
    for (Ob i = 1; i <= atom_count; ++i) {
        rep_table_.insert({i, {0, 0, 0}});
    }

    if (POMAGMA_DEBUG_LEVEL) {
        assert_valid();
    }
}

// Aka update_term (python).
inline void Engine::rep_normalize(Ob& ob) const {
    while (Ob rep = map_find(rep_table_, ob).red) {
        if (rep == ob) return;
        ob = rep;
    }
}

inline const std::unordered_map<Ob, Ob>& Engine::abstract(Ob body) const {
    static const std::unordered_map<Ob, Ob> empty;  // Just a default value.
    auto i = abstract_table_.find(body);
    return (i == abstract_table_.end()) ? empty : i->second;
}

Ob Engine::abstract(Ob var, Ob body) {
    // Rules BOT, TOP.
    if (body == atom_TOP or body == atom_BOT) {
        return body;
    }
    auto i = abstract_table_.find(body);
    if (i != abstract_table_.end()) {
        auto j = i->second.find(var);
        if (j != i->second.end()) {
            return j->second;
        }
    }
    return get_app(atom_K, body);  // Rule K.
}

Ob Engine::create_app(Ob lhs, Ob rhs) {
    assert_pos(lhs);
    assert_pos(rhs);
    rep_normalize(lhs);
    rep_normalize(rhs);
    POMAGMA_ASSERT1(lhs != atom_BOT, "called create_app(BOT, -)");
    POMAGMA_ASSERT1(lhs != atom_TOP, "called create_app(TOP, -)");

    // Precompute abstractions.
    std::unordered_map<Ob, Ob> abs_term;
    const std::unordered_map<Ob, Ob>& abs_lhs = abstract(lhs);
    const std::unordered_map<Ob, Ob>& abs_rhs = abstract(rhs);
    std::unordered_set<Ob> vars;
    for (const auto& i : abs_lhs) {
        vars.insert(i.first);
    }
    for (const auto& i : abs_rhs) {
        vars.insert(i.first);
    }
    for (const Ob var : vars) {
        const Ob abs_lhs_var = map_get(abs_lhs, var, 0);
        const Ob abs_rhs_var = map_get(abs_rhs, var, 0);
        if (abs_lhs_var) {
            if (abs_rhs_var) {
                // Rule S.
                abs_term[var] =
                    get_app(get_app(atom_S, abs_lhs_var), abs_rhs_var);
            } else {
                // Rule C.
                abs_term[var] = get_app(get_app(atom_C, abs_lhs_var), rhs);
            }
        } else {
            if (abs_rhs_var == atom_I) {
                abs_term[var] = lhs;  // Rule eta.
            } else {
                // Rule B.
                abs_term[var] = get_app(get_app(atom_B, lhs), abs_rhs_var);
            }
        }
    }

    // Create a new term.
    const Ob val = 1 + rep_table_.size();
    rep_table_.insert({val, {lhs, rhs, val}});
    LRv_table_.insert({{lhs, rhs}, val});
    Lrv_table_[lhs].insert({rhs, val});
    Lrv_table_[rhs].insert({lhs, val});
    Vlr_table_[val].insert({lhs, rhs});
    if (not abs_term.empty()) {
        abstract_table_[val] = std::move(abs_term);
    }

    return val;
}

inline Ob Engine::get_app(Ob lhs, Ob rhs) {
    assert_pos(lhs);
    assert_pos(rhs);
    rep_normalize(lhs);
    rep_normalize(rhs);

    // First check cache.
    {
        auto i = LRv_table_.find({lhs, rhs});
        if (i != LRv_table_.end()) {
            return i->second;
        }
    }

    return create_app(lhs, rhs);
}

static inline Ob pop(std::vector<Ob>& stack, Ob& end_var) {
    if (stack.empty()) {
        Ob ob = stack.back();
        stack.pop_back();
        return ob;
    } else {
        return end_var--;
    }
}

Ob Engine::app(Ob lhs, Ob rhs, size_t& budget, Ob begin_var) {
    assert_pos(lhs);
    assert_pos(rhs);
    rep_normalize(lhs);
    rep_normalize(rhs);

    // First check the cache.
    {
        auto i = LRv_table_.find({lhs, rhs});
        if (i != LRv_table_.end()) {
            return i->second;
        }
    }

    // Eagerly linear-beta-eta head reduce; beta reduce within budget.
    Ob head = lhs;
    Ob end_var = begin_var;
    std::vector<Ob> stack;
    bool normalized = true;     // = not pending (python).
    while (not is_var(head)) {  // tail call optimized.
        if (is_app(head)) {
            const Term& term = map_find(rep_table_, head);
            head = term.lhs;
            stack.push_back(term.rhs);
            rep_normalize(head);
            rep_normalize(stack.back());
            continue;
        }
        switch (head) {
            case atom_BOT: {
                POMAGMA_ASSERT1(stack.size() < 1, "not in linear normal form");
            } break;
            case atom_TOP: {
                POMAGMA_ASSERT1(stack.size() < 1, "not in linear normal form");
            } break;
            case atom_I: {
                POMAGMA_ASSERT1(stack.size() < 1, "not in linear normal form");
                head = pop(stack, end_var);
                continue;
            } break;
            case atom_K: {
                POMAGMA_ASSERT1(stack.size() < 2, "not in linear normal form");
                head = pop(stack, end_var);
                pop(stack, end_var);
                continue;
            } break;
            case atom_B: {
                POMAGMA_ASSERT1(stack.size() < 3, "not in linear normal form");
                const Ob x = pop(stack, end_var);
                const Ob y = pop(stack, end_var);
                const Ob z = pop(stack, end_var);
                const Ob yz = app(y, z, budget, end_var);  // May merge.
                head = app(x, yz, budget, end_var);        // May merge.
                continue;
            } break;
            case atom_C: {
                POMAGMA_ASSERT1(stack.size() < 3, "not in linear normal form");
                const Ob x = pop(stack, end_var);
                const Ob y = pop(stack, end_var);
                const Ob z = pop(stack, end_var);
                const Ob xz = app(x, z, budget, end_var);  // May merge.
                head = app(xz, y, budget, end_var);        // May merge.
                continue;
            } break;
            case atom_S: {
                if (budget == 0 and stack.size() >= 3) {
                    Ob rhs = stack[stack.size() - 3];
                    if (is_app(rhs)) {  // nonlinear
                        // TODO Set flag to not memoize if budget-limited.
                        // What we really want here is to save the reducer
                        // via something like setjmp; yield a partial value
                        // to an any-time result stream; then continue computing
                        // with until next budget cycle. And only memoize
                        // total values. But how?
                        normalized = false;
                        break;
                    }
                }
                budget -= 1;
                POMAGMA_ASSERT1(stack.size() < 3 or is_app(stack[2]),
                                "not in linear normal form");
                const Ob x = pop(stack, end_var);
                const Ob y = pop(stack, end_var);
                const Ob z = pop(stack, end_var);
                const Ob xz = app(x, z, budget, end_var);  // May merge.
                const Ob yz = app(y, z, budget, end_var);  // May merge.
                head = app(xz, yz, budget, end_var);       // May merge.
                continue;
            } break;
            default:
                POMAGMA_ERROR("unreachable");
        }
        break;
    }

    // Reduce arguments.
    while (not stack.empty()) {
        Ob arg = stack.back();
        stack.pop_back();
        if (budget and is_app(arg)) {
            arg = reduce(arg, budget, end_var);  // May merge.
        }
        head = get_app(head, arg);
    }

    // Abstract out variables.
    for (Ob var = end_var; var != begin_var; ++var) {
        head = abstract(var, head);
    }

    // Update database with result.
    {
        auto inserted = LRv_table_.insert({{lhs, rhs}, head});
        if (likely(inserted.second)) {
            if (normalized) {
                rep_table_.find(head)->second.red = 0;
            }
        } else {
            const Ob old = inserted.first->second;
            if (unlikely(old != head)) {
                Ob& old_rep = rep_table_.find(old)->second.red;
                Ob& head_rep = rep_table_.find(head)->second.red;
                POMAGMA_ASSERT((old_rep == 0) xor (head_rep == 0),
                               "TODO what to do?");
                if (old_rep == 0) {
                    head_rep = old;
                    merge(head);
                } else {
                    old_rep = head;
                    merge(old);
                }
                rep_normalize(head);
            }
        }
    }

    assert_weak_red(head);
    return head;
}

Ob Engine::reduce(Ob ob, size_t& budget, Ob begin_var) {
    POMAGMA_ASSERT1(budget, "Do not call reduce() with zero budget");
    assert_pos(ob);
    rep_normalize(ob);
    if (is_normal(ob)) return ob;

    POMAGMA_ASSERT(is_app(ob), "programmer error");
    return app(get_lhs(ob), get_rhs(ob), budget, begin_var);
}

void Engine::merge(Ob dep) {
    POMAGMA_ASSERT1(merge_queue_.empty(), "programmer error");
    merge_queue_.insert(dep);
    do {
        auto i = merge_queue_.begin();
        dep = *i;
        merge_queue_.erase(i);
        Ob rep = rep_table_[dep].red;
        POMAGMA_ASSERT_NE(dep, rep);

        // Merge occurrences of dep as lhs.
        for (const auto& pair : Lrv_table_[dep]) {
            Rlv_table_[pair.first].erase({dep, pair.second});
            Rlv_table_[pair.first].insert({rep, pair.second});

            LRv_table_.erase({dep, pair.first});
            auto inserted = LRv_table_.insert({{rep, pair.first}, pair.second});
            if (not inserted.second and inserted.first->second != pair.second) {
                // Which direction? Is this even confluent?
                TODO("merge inserted.first->second with pair.second");
            }

            Lrv_table_[rep].insert(pair);
        }
        Lrv_table_[dep].clear();

        // Merge occurrences of dep as rhs.
        for (const auto& pair : Rlv_table_[dep]) {
            Lrv_table_[pair.first].erase({dep, pair.second});
            Lrv_table_[pair.first].insert({rep, pair.second});

            LRv_table_.erase({pair.first, dep});
            auto inserted = LRv_table_.insert({{pair.first, rep}, pair.second});
            if (not inserted.second and inserted.first->second != pair.second) {
                TODO("merge inserted.first->second with pair.second");
            }

            Rlv_table_[rep].insert(pair);
        }
        Rlv_table_[dep].clear();

        // Merge occurrences of dep as val.
        for (const auto& pair : Vlr_table_[dep]) {
            LRv_table_[pair] = rep;
            Lrv_table_[pair.first].erase({pair.second, dep});
            Lrv_table_[pair.first].insert({pair.second, rep});
            Rlv_table_[pair.second].erase({pair.first, dep});
            Rlv_table_[pair.second].insert({pair.first, rep});
        }
        Vlr_table_[dep].clear();

        // Merge occurrences of dep as body in abstract_table_.
        // TODO is this necessary?

    } while (not merge_queue_.empty());
}

}  // namespace reducer
}  // namespace pomagma
