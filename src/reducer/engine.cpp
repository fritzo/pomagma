#include <pomagma/reducer/engine.hpp>

namespace pomagma {
namespace reducer {

Engine::Engine() {
    const size_t dim = 1 + atom_count;  // null + atoms
    rep_.resize(dim);
    Lrv_table_.resize(dim);
    Rlv_table_.resize(dim);
    Vlr_table_.resize(dim);

    // Atoms are themselves reduced.
    for (size_t i = 1; i <= atom_count; ++i) {
        rep_[i].red = i;
    }
}

Engine::~Engine() {
    POMAGMA_INFO("Engine ob count = " << (rep_.size() - 1));
    POMAGMA_INFO("Engine app count = " << LRv_table_.size());
}

bool Engine::validate(std::vector<std::string>& errors) const {
    errors.push_back("TODO Validate all terms are linear normal forms.");
    return true;
}

Ob Engine::app(Ob lhs, Ob rhs) {
    assert_pos(lhs);
    assert_pos(rhs);

    // Check cache first.
    {
        auto i = LRv_table_.find(std::make_pair(lhs, rhs));
        if (i != LRv_table_.end()) {
            return i->second;
        }
    }

    // Linearly normalize.
    bool normalized __attribute__((unused)) = true;
    while (true) {  // tail call optimized.
        if (not is_app(lhs)) {
            if (lhs == atom_I) {
                return rhs;
            }
            if (lhs == atom_BOT or lhs == atom_TOP) {
                return lhs;
            }
            break;
        }
        const Ob lhs_lhs = get_lhs(lhs);
        if (not is_app(lhs_lhs)) {
            if (lhs_lhs == atom_K) {
                return get_rhs(lhs);
            }
            break;
        }
        const Ob lhs_lhs_lhs = get_lhs(lhs_lhs);
        if (not is_app(lhs_lhs_lhs)) {
            if (lhs_lhs_lhs == atom_B) {
                Ob x = get_rhs(lhs_lhs);
                Ob y = get_rhs(lhs);
                Ob z = rhs;
                lhs = x;
                rhs = app(y, z);  // Recurse.
                continue;
            }
            if (lhs_lhs_lhs == atom_C) {
                Ob x = get_rhs(lhs_lhs);
                get_rhs(lhs);
                Ob z = rhs;
                lhs = app(x, z);  // Recurse.
                rhs = z;
                continue;
            }
            if (lhs_lhs_lhs == atom_S) {
                if (is_app(rhs)) {  // nonlinear
                    normalized = false;
                    break;
                }
                Ob x = get_rhs(lhs_lhs);
                Ob y = get_rhs(lhs);
                Ob z = rhs;
                lhs = app(x, z);  // Recurse.
                rhs = app(y, z);  // Recurse.
                continue;
            }
            break;
        }
        break;
    }

    // Create.
    Ob& val = LRv_table_[std::make_pair(lhs, rhs)];
    if (not val) {
        val = rep_.size();
        rep_.push_back({lhs, rhs, 0});  // TODO get from free-list?
        LRv_table_.insert({{lhs, rhs}, val});
        Lrv_table_.resize(rep_.size());
        Lrv_table_[lhs].insert({rhs, val});
        Rlv_table_.resize(rep_.size());
        Rlv_table_[rhs].insert({lhs, val});
        Vlr_table_.resize(rep_.size());
        Vlr_table_[val].insert({lhs, rhs});

#if 0
        // -------- BEGIN --------
        // Is the rep-chain actually needed outside of merging?
        if (normalized and is_normal(lhs) and is_normal(rhs)) {
            rep_[val].red = val;
        }
    } else if (Ob red_val = rep_[val].red) {
        val = red_val;
        // -------- END --------
#endif  // 0
    }

    assert_weak_red(val);
    return val;
}

bool Engine::occurs(Ob var, Ob body) {
    // TODO memoize
    POMAGMA_ASSERT1(is_var(var), "occurs() called on non-variable");
    return (var == body) or (is_app(body) and (occurs(var, get_lhs(body)) or
                                               occurs(var, get_rhs(body))));
}

Ob Engine::abstract(Ob var, Ob body) {
    // TODO memoize
    POMAGMA_ASSERT1(is_var(var), "abstract() called on non-variable");
    if (body == var) {
        return atom_I;
    } else if (body == atom_BOT or body == atom_TOP) {
        return body;
    } else if (not occurs(var, body)) {
        return app(atom_K, body);
    }

    // Otherwise the ob must be an application.
    POMAGMA_ASSERT1(is_app(body), "programmer error");
    const Ob lhs = get_lhs(body);
    const Ob rhs = get_rhs(body);
    if (occurs(var, lhs)) {
        if (occurs(var, rhs)) {
            return app(app(atom_S, abstract(var, lhs)), abstract(var, rhs));
        } else {
            return app(app(atom_C, abstract(var, lhs)), rhs);
        }
    } else {
        POMAGMA_ASSERT1(occurs(var, rhs), "programmer error");
        if (rhs == var) {
            return lhs;  // eta
        } else {
            return app(app(atom_B, lhs), abstract(var, rhs));
        }
    }
}

namespace {

inline Ob pop(std::vector<Ob>& stack, Ob& end_var) {
    if (stack.empty()) {
        Ob ob = stack.back();
        stack.pop_back();
        return ob;
    } else {
        return end_var--;
    }
}

}  // namespace

Ob Engine::reduce(Ob ob, size_t& budget, Ob begin_var) {
    assert_pos(ob);
    POMAGMA_ASSERT1(budget, "Do not call reduce() with zero budget");

    // Check cache first.
    if (Ob ob_red = rep_[ob].red) {
        return ob_red;
    }

    Ob end_var = begin_var;
    std::vector<Ob> stack;

    // Head reduce, applying fresh variables as needed.
    // TODO check cache to exit early if reduced form is found?
    // TODO for union-find algorithm, also merge all intermediate terms.
    while (not is_var(ob)) {
        while (is_app(ob)) {
            stack.push_back(get_rhs(ob));
            ob = get_lhs(ob);
        }
        switch (ob) {
            case atom_BOT: {
                POMAGMA_ASSERT1(stack.size() < 1, "not in linear normal form");
            } break;
            case atom_TOP: {
                POMAGMA_ASSERT1(stack.size() < 1, "not in linear normal form");
            } break;
            case atom_I: {
                POMAGMA_ASSERT1(stack.size() < 1, "not in linear normal form");
                ob = pop(stack, end_var);
            } break;
            case atom_K: {
                POMAGMA_ASSERT1(stack.size() < 2, "not in linear normal form");
                ob = pop(stack, end_var);
                pop(stack, end_var);
            } break;
            case atom_B: {
                POMAGMA_ASSERT1(stack.size() < 3, "not in linear normal form");
                Ob x = pop(stack, end_var);
                Ob y = pop(stack, end_var);
                Ob z = pop(stack, end_var);
                ob = app(x, app(y, z));
            } break;
            case atom_C: {
                POMAGMA_ASSERT1(stack.size() < 3, "not in linear normal form");
                Ob x = pop(stack, end_var);
                Ob y = pop(stack, end_var);
                Ob z = pop(stack, end_var);
                ob = app(app(x, z), y);
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
                        break;
                    }
                }
                budget -= 1;
                POMAGMA_ASSERT1(stack.size() < 3 or is_app(stack[2]),
                                "not in linear normal form");
                Ob x = pop(stack, end_var);
                Ob y = pop(stack, end_var);
                Ob z = pop(stack, end_var);
                ob = app(app(x, z), app(y, z));
            } break;
            default:
                POMAGMA_ASSERT1(is_var(ob), "not a variable");
        }
    }

    // Reduce arguments.
    while (not stack.empty()) {
        Ob arg = stack.back();
        stack.pop_back();
        if (budget and is_app(arg)) {
            arg = reduce(arg, budget, end_var);  // May induce merges.
        }
        ob = app(ob, arg);
    }

    // Abstract out variables.
    for (Ob var = end_var; var != begin_var; ++var) {
        ob = abstract(var, ob);
    }

    return ob;
}

Ob Engine::memoized_reduce(Ob ob, size_t budget, Ob begin_var) {
    assert_pos(ob);

    Ob& ob_red = rep_[ob].red;
    if (not ob_red) {
        ob_red = reduce(ob, budget, begin_var);
    }
    if (ob_red != ob) {
        merge(ob);
    }
    return ob_red;
}

void Engine::merge(Ob dep) {
    POMAGMA_ASSERT1(merge_queue_.empty(), "programmer error");
    merge_queue_.insert(dep);
    do {
        auto i = merge_queue_.begin();
        dep = *i;
        merge_queue_.erase(i);
        Ob rep = rep_[dep].red;
        POMAGMA_ASSERT_NE(dep, rep);

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

        for (const auto& pair : Vlr_table_[dep]) {
            LRv_table_[pair] = rep;
            Lrv_table_[pair.first].erase({pair.second, dep});
            Lrv_table_[pair.first].insert({pair.second, rep});
            Rlv_table_[pair.second].erase({pair.first, dep});
            Rlv_table_[pair.second].insert({pair.first, rep});
        }
        Vlr_table_[dep].clear();
    } while (not merge_queue_.empty());
}

}  // namespace reducer
}  // namespace pomagma
