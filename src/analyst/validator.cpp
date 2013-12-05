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
    for (const Corpus::Term * term : diff.added) {
        schedule(term);
    }
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
    auto i = m_cache.find(term);
    delete i->second;
    m_cache.erase(i);

    TODO("cancel task");
}

void Validator::schedule (const Corpus::Term * term)
{
    if (term->ob) {
        m_cache.insert(std::make_pair(
            term,
            new Approximation(m_approximator.known(term->ob))));
    } else {
        m_cache.insert(std::make_pair(
            term,
            new Approximation(m_approximator.unknown())));

        TODO("schedule task");
    }
}

inline Approximation & Validator::get (const Corpus::Term * term)
{
    auto i = m_cache.find(term);
    POMAGMA_ASSERT(i != m_cache.end(), "term not found in cache");
    return * (i->second);
}

inline bool Validator::try_set (
        const Corpus::Term * term,
        Approximation && approx)
{
    auto i = m_cache.find(term);
    if (i == m_cache.end()) {
        m_cache.insert(
            std::make_pair(term, new Approximation(std::move(approx))));
        return true;
    } else {
        Approximation & current = * (i->second);
        if (approx != current) {
            approx = current;
            return true;
        } else {
            return false;
        }
    }
}

Approximation Validator::approximate (const Corpus::Term * term)
{
    const std::string & name = term->name;
    const Corpus::Term * arg0 = term->arg0;
    const Corpus::Term * arg1 = term->arg1;

    switch (term->arity) {

        case Corpus::Term::OB:
            return m_approximator.known(term->ob);

        case Corpus::Term::HOLE:
            return m_approximator.unknown();

        case Corpus::Term::VARIABLE:
            TODO("look up variable in table");

        case Corpus::Term::NULLARY_FUNCTION:
            return m_approximator.find(name);

        case Corpus::Term::INJECTIVE_FUNCTION:
            return m_approximator.find(name, get(arg0));

        case Corpus::Term::BINARY_FUNCTION:
        case Corpus::Term::SYMMETRIC_FUNCTION:
        case Corpus::Term::BINARY_RELATION:
            return m_approximator.find(name, get(arg0), get(arg1));
    }

    POMAGMA_ERROR("should never get here");
}

void Validator::process (Task * task)
{
    const Corpus::Term * term = task->term;
    if (try_set(term, approximate(term))) {
        TODO("enqueue further work");
    }
}

bool Validator::try_work ()
{
    TODO("");
    return false;
}

} // namespace pomagma
