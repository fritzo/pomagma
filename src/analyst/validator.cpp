#include "validator.hpp"

namespace pomagma
{

Validator::Validator (
        Approximator & approximator,
        size_t thread_count)
    : m_approximator(approximator)
{
    POMAGMA_ASSERT_LT(0, thread_count);
    //TODO("start workers");
}

Validator::~Validator ()
{
    //TODO("stop workers");
}

void Validator::update (const Corpus::Diff & diff)
{
    for (const Corpus::Term * term : diff.removed) {
        cancel(term);
    }
    TODO("restart changed terms");
    TODO("schedule new tasks");
}

Approximator::Validity Validator::is_valid (const Corpus::Term * term)
{
    auto i = m_cache.find(term);
    if (i != m_cache.end()) {
        return m_approximator.is_valid(* i->second);
    } else {
        return Approximator::Validity::unknown();
    }
}

void Validator::cancel (const Corpus::Term * term)
{
    m_cache.erase(term);
    TODO("cancel task");
}

void Validator::schedule (const Corpus::Term * term __attribute__((unused)))
{
    TODO("schedule task");
}

} // namespace pomagma
