#pragma once

#include <pomagma/analyst/approximate.hpp>
#include <pomagma/analyst/cached_approximator.hpp>
#include <pomagma/analyst/corpus.hpp>
#include <pomagma/util/async_map.hpp>
#include <pomagma/util/unique_set.hpp>
#include <set>
#include <thread>
#include <mutex>

namespace pomagma {

class Validator : noncopyable {
    typedef AsyncMap<const Corpus::Term *, HashedApproximation> Cache;

    class Task {
       public:
        Task(Validator &validator, const Corpus::Term *term,
             Cache::Callback callback)
            : m_validator(validator),
              m_term(term),
              m_callback(callback),
              m_state(term->arg1 ? 3 : term->arg0 ? 2 : 1) {
            if (term->arg0) {
                m_validator.m_cache.find_async(
                    term->arg0, std::bind(&Task::operator(), this, _1));
            }
            if (term->arg1) {
                m_validator.m_cache.find_async(
                    term->arg1, std::bind(&Task::operator(), this, _1));
            }
            operator()(nullptr);
        }

        void operator()(const HashedApproximation *) {
            if (--m_state == 0) {
                m_validator.m_cached_approximator.find_async(
                    m_validator.convert(m_term), m_callback);
                delete this;
            }
        }

       private:
        Validator &m_validator;
        const Corpus::Term *m_term;
        Cache::Callback m_callback;
        std::atomic<int> m_state;
    };

    struct AsyncFunction {
        Validator &validator;

        void operator()(const Corpus::Term *term, Cache::Callback callback) {
            new Task(validator, term, callback);
        }
    };

   public:
    explicit Validator(Approximator &approximator)
        : m_approximator(approximator),
          m_cached_approximator(approximator),
          m_function({*this}),
          m_cache(std::bind(&AsyncFunction::operator(), &m_function, _1, _2)) {}

    struct AsyncValidity {
        Approximator::Validity validity;
        bool pending;
    };

    std::vector<AsyncValidity> validate(
        const std::vector<Corpus::LineOf<const Corpus::Term *>> &lines,
        Corpus::Linker &linker);

    AsyncValidity is_valid(const Corpus::Term *term) {
        if (auto approx = m_cache.find(term)) {
            return AsyncValidity(
                {m_approximator.is_valid(approx->approx), false});
        } else {
            return AsyncValidity({Approximator::Validity::unknown(), true});
        }
    }

   private:
    static bool is_ambiguous(const Approximator::Validity &validity) {
        return validity.is_top == Approximator::MAYBE or
               validity.is_bot == Approximator::MAYBE;
    }

    CachedApproximator::Term convert(const Corpus::Term *term) {
        POMAGMA_ASSERT1(term->arity != Corpus::Term::VARIABLE,
                        "tried to convert a variable");
#define POMAGMA_ASSERT_ARITY(arity)                                       \
    static_assert(                                                        \
        int(Corpus::Term::arity) == int(CachedApproximator::Term::arity), \
        "arity mismatch: " #arity);
        POMAGMA_ASSERT_ARITY(OB)
        POMAGMA_ASSERT_ARITY(HOLE)
        POMAGMA_ASSERT_ARITY(NULLARY_FUNCTION)
        POMAGMA_ASSERT_ARITY(INJECTIVE_FUNCTION)
        POMAGMA_ASSERT_ARITY(BINARY_FUNCTION)
        POMAGMA_ASSERT_ARITY(SYMMETRIC_FUNCTION)
        POMAGMA_ASSERT_ARITY(UNARY_RELATION)
        POMAGMA_ASSERT_ARITY(BINARY_RELATION)
#undef POMAGMA_ASSERT_ARITY

        auto name = term->name;
        auto arity = static_cast<CachedApproximator::Term::Arity>(term->arity);
        auto arg0 = term->arg0 ? m_cache.find(term->arg0) : nullptr;
        auto arg1 = term->arg1 ? m_cache.find(term->arg1) : nullptr;
        auto ob = term->ob;

        return CachedApproximator::Term({arity, name, arg0, arg1, ob});
    }

    Approximator &m_approximator;
    CachedApproximator m_cached_approximator;
    AsyncFunction m_function;
    Cache m_cache;
};

}  // namespace pomagma
