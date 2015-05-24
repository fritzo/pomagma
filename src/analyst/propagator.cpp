#include "propagator.hpp"

namespace pomagma
{

size_t Propagator::propagate_step ()
{
    size_t change_count = 0;

    // first pass up parse trees replaces upper, lower
    for (auto i = terms.begin(); i != terms.end(); ++i) {
        const Corpus::Term * term = *i;
        change_count += propagate_up(term);
        change_count += propagate_up(term);
    }

    // second pass down parse trees updates nupper, nlower
    for (auto i = terms.rbegin(); i != terms.rend(); ++i) {
        const Corpus::Term * term = *i;
        change_count += propagate_nupper(term);
        change_count += propagate_nlower(term);
    }

    return change_count;
}

bool Propagator::propagate_upper (const Corpus::Term * term)
{
    // Ask cached_approximator for computed value;
    // if it exists, replace old value with new.
    CachedApproximator::Task task = {
        UPPER,
        term->arity,
        term->name,
        term->arg0 ? m_bounds.get(UPPER, term->arg0) : nullptr,
        term->arg1 ? m_bounds.get(UPPER, term->arg1) : nullptr,
        term->ob
    };
    const HashedSet * bound = m_cached_approximator.try_find_upper(task);
    return bound and m_bounds.replace(UPPER, term, bound);
}

size_t Propagator::propagate_ (const Corpus::Term * term)
{
    // For each direction,
    // ask cached_approximator for computed value
    // if it exists, atomically union new value into old value.

    size_t change_count = 0;

    switch (term->arity) {
        case Corpus::Term::BINARY_RELATION: {
            const HashedSet * val_nupper = m_bounds.get(NUPPER, term);
            {
                const HashedSet * lhs = m_bounds.get(UPPER, term->arg0);
                const HashedSet * rhs = m_bounds.get(NUPPER, term->arg1);
                const HashedSet * updated =
                    m_cached_approximator.binary_function_val_rhs(
                        term->name, lhs, val, rhs);
                if (updated and updated != lhs) {
                    m_bounds.set(NUPPER, term->arg0);
                    change_count += 1;
                }
            }
            {
                const HashedSet * lhs = m_bounds.get(NUPPER, term->arg0);
                const HashedSet * rhs = m_bounds.get(UPPER, term->arg1);
                const HashedSet * updated =
                    m_cached_approximator.binary_function_val_lhs(
                        term->name, lhs, val, rhs);
                if (updated and updated != lhs) {
                    m_bounds.set(NUPPER, term->arg1);
                    change_count += 1;
                }
            }
        } break;

        default: TODO("handle other cases");
    }

    return change_count;
}

} // namespace pomagma
