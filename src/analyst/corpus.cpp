#include "corpus.hpp"
#include <pomagma/util/unique_set.hpp>
#include <map>
#include <queue>

namespace pomagma {

//----------------------------------------------------------------------------
// Dag

class Corpus::Dag {
   public:
    explicit Dag(Signature &signature)
        : m_signature(signature), m_new_term(new Term()) {}

    const Term *semi_true() { return nullary_function("I"); }
    const Term *semi_false() { return nullary_function("BOT"); }
    const Term *semi_and(const Term *lhs, const Term *rhs) {
        if (lhs > rhs) {
            std::swap(lhs, rhs);
        }
        return binary_function("APP", lhs, rhs);
    }

    const Term *hole() { return get(Term(Term::HOLE)); }
    const Term *variable(const std::string &name) {
        return get(Term(Term::VARIABLE, name));
    }
    const Term *nullary_function(const std::string &name) {
        if (auto *fun = m_signature.nullary_function(name)) {
            if (Ob ob = fun->find()) {
                return get(Term(ob));
            }
        }
        return get(Term(Term::NULLARY_FUNCTION, name));
    }
    const Term *injective_function(const std::string &name, const Term *arg) {
        if (arg->ob) {
            if (auto *fun = m_signature.injective_function(name)) {
                if (Ob ob = fun->find(arg->ob)) {
                    return get(Term(ob));
                }
            }
        }
        return get(Term(Term::INJECTIVE_FUNCTION, name, arg));
    }
    const Term *binary_function(const std::string &name, const Term *lhs,
                                const Term *rhs) {
        if (lhs->ob and rhs->ob) {
            if (auto *fun = m_signature.binary_function(name)) {
                if (Ob ob = fun->find(lhs->ob, rhs->ob)) {
                    return get(Term(ob));
                }
            }
        }
        return get(Term(Term::BINARY_FUNCTION, name, lhs, rhs));
    }
    const Term *symmetric_function(const std::string &name, const Term *lhs,
                                   const Term *rhs) {
        if (lhs->ob and rhs->ob) {
            if (auto *fun = m_signature.symmetric_function(name)) {
                if (Ob ob = fun->find(lhs->ob, rhs->ob)) {
                    return get(Term(ob));
                }
            }
        }
        if (lhs > rhs) {
            std::swap(lhs, rhs);
        }
        return get(Term(Term::SYMMETRIC_FUNCTION, name, lhs, rhs));
    }
    const Term *unary_relation(const std::string &name, const Term *arg) {
        if (arg->ob) {
            if (auto *rel = m_signature.unary_relation(name)) {
                if (rel->find(arg->ob)) {
                    return semi_true();
                }
            }
            std::string negated = m_signature.negate(name);
            if (auto *negated_rel = m_signature.unary_relation(negated)) {
                if (negated_rel->find(arg->ob)) {
                    return semi_false();
                }
            }
        }
        return get(Term(Term::UNARY_RELATION, name, arg));
    }
    const Term *binary_relation(const std::string &name, const Term *lhs,
                                const Term *rhs) {
        if (lhs->ob and rhs->ob) {
            if (auto *rel = m_signature.binary_relation(name)) {
                if (rel->find(lhs->ob, rhs->ob)) {
                    return semi_true();
                }
            }
            std::string negated = m_signature.negate(name);
            if (auto *negated_rel = m_signature.binary_relation(negated)) {
                if (negated_rel->find(lhs->ob, rhs->ob)) {
                    return semi_false();
                }
            }
        }
        return get(Term(Term::BINARY_RELATION, name, lhs, rhs));
    }
    const Term *equal(const Term *lhs, const Term *rhs) {
        if (lhs->ob and rhs->ob and lhs == rhs) {
            return semi_true();
        } else {
            const Term *less_lhs_rhs = binary_relation("LESS", lhs, rhs);
            const Term *less_rhs_lhs = binary_relation("LESS", rhs, lhs);
            return semi_and(less_lhs_rhs, less_rhs_lhs);
        }
    }

    const Histogram &histogram() const { return m_histogram; }

   private:
    const Term *get(Term &&key) {
        *m_new_term = key;
        const Term *term = m_terms.insert(m_new_term);
        m_histogram.add(term);
        if (term == m_new_term) {
            m_new_term = new Term();
        }
        return term;
    }

    Signature &m_signature;
    Term *m_new_term;
    UniqueSet<Term, Term::Hash, false> m_terms;
    Histogram m_histogram;
};

//----------------------------------------------------------------------------
// Parser

class Corpus::Reducer {
   public:
    explicit Reducer(Dag &dag) : m_dag(dag) {}

    typedef const Corpus::Term *Term;

    Term reduce(const std::string &token, const NullaryFunction *) {
        return m_dag.nullary_function(token);
    }

    Term reduce(const std::string &token, const InjectiveFunction *, Term key) {
        return m_dag.injective_function(token, key);
    }

    Term reduce(const std::string &token, const BinaryFunction *, Term lhs,
                Term rhs) {
        return m_dag.binary_function(token, lhs, rhs);
    }

    Term reduce(const std::string &token, const SymmetricFunction *, Term lhs,
                Term rhs) {
        return m_dag.binary_function(token, lhs, rhs);
    }

    Term reduce(const std::string &token, const UnaryRelation *, Term key) {
        return m_dag.unary_relation(token, key);
    }

    Term reduce(const std::string &token, const BinaryRelation *, Term lhs,
                Term rhs) {
        return m_dag.binary_relation(token, lhs, rhs);
    }

    Term reduce_equal(Term lhs, Term rhs) { return m_dag.equal(lhs, rhs); }

    Term reduce_hole() { return m_dag.hole(); }

    Term reduce_var(const std::string &name) { return m_dag.variable(name); }

    Term reduce_error(const std::string &) { return m_dag.hole(); }

   private:
    Dag &m_dag;
};

class Corpus::Parser : public ExprParser<Corpus::Reducer> {
   public:
    Parser(Signature &signature, Corpus::Dag &dag,
           std::vector<std::string> &error_log)
        : ExprParser<Corpus::Reducer>(signature, m_reducer, error_log),
          m_reducer(dag) {}

   private:
    Reducer m_reducer;
};

//----------------------------------------------------------------------------
// Linker

Corpus::Linker::Linker(Dag &dag, std::vector<std::string> &error_log)
    : m_dag(dag), m_error_log(error_log), m_definitions(), m_ground_terms() {}

inline void Corpus::Linker::define(const std::string &name, const Term *term) {
    const Term *var = m_dag.variable(name);
    auto pair = m_definitions.insert(std::make_pair(var, term));
    if (not pair.second) {
        POMAGMA_DEBUG("multiple definition of: " << name);
        m_error_log.push_back("multiple definition of: " + name);
    }
}

void Corpus::Linker::accum_free(const Term *term,
                                std::unordered_set<const Term *> &free) {
    if (term->arity == Term::VARIABLE) {
        free.insert(term);
    } else if (term->arg1) {
        accum_free(term->arg0, free);
        accum_free(term->arg1, free);
    } else if (term->arg0) {
        accum_free(term->arg0, free);
    }
}

void Corpus::Linker::finish() {
    std::multimap<const Term *, const Term *> occurrences;
    std::unordered_map<const Term *, size_t> free_counts;
    std::queue<const Term *> ground_terms;

    for (const auto &pair : m_definitions) {
        const Term *var = pair.first;
        const Term *term = pair.second;
        std::unordered_set<const Term *> free;
        accum_free(term, free);
        free_counts[term] = free.size();
        if (free.empty()) {
            ground_terms.push(var);
        } else {
            for (const Term *subterm : free) {
                occurrences.insert(std::make_pair(subterm, var));
            }
        }
    }

    while (not ground_terms.empty()) {
        const Term *var = ground_terms.front();
        ground_terms.pop();
        const Term *linked = link(m_definitions.find(var)->second);
        m_ground_terms.insert(var);
        m_definitions[var] = linked;
        auto range = occurrences.equal_range(var);
        for (; range.first != range.second; occurrences.erase(range.first++)) {
            const Term *superterm = range.first->second;
            if (--free_counts[superterm] == 0) {
                ground_terms.push(superterm);
            }
        }
    }

    POMAGMA_DEBUG("linked " << m_ground_terms.size() << " / "
                            << m_definitions.size() << " terms");
}

const Corpus::Term *Corpus::Linker::link(const Term *term) {
    const std::string &name = term->name;
    const Term *const arg0 = term->arg0;
    const Term *const arg1 = term->arg1;

    switch (term->arity) {
        case Term::OB:
        case Term::HOLE:
        case Term::NULLARY_FUNCTION:
            return term;

        case Term::INJECTIVE_FUNCTION:
            return m_dag.injective_function(name, link(arg0));

        case Term::BINARY_FUNCTION:
            return m_dag.binary_function(name, link(arg0), link(arg1));

        case Term::SYMMETRIC_FUNCTION:
            return m_dag.symmetric_function(name, link(arg0), link(arg1));

        case Term::UNARY_RELATION:
            return m_dag.unary_relation(name, link(arg0));

        case Term::BINARY_RELATION:
            return m_dag.binary_relation(name, link(arg0), link(arg1));

        case Term::VARIABLE:
            if (m_ground_terms.find(term) != m_ground_terms.end()) {
                return m_definitions.find(term)->second;
            } else {
                if (m_definitions.find(term) == m_definitions.end()) {
                    POMAGMA_DEBUG("missing definition of: " << name);
                    m_error_log.push_back("missing definition of: " + name);
                }
                return term;
            }
    }

    POMAGMA_ERROR("unreachable");
}

const Corpus::Term *Corpus::Linker::approximate(const Term *term,
                                                size_t depth) {
    m_temp_max_depth = depth;
    return approximate(term);
}

const Corpus::Term *Corpus::Linker::approximate(const Term *term) {
    const std::string &name = term->name;
    const Term *const arg0 = term->arg0;
    const Term *const arg1 = term->arg1;

    switch (term->arity) {
        case Term::OB:
        case Term::HOLE:
        case Term::NULLARY_FUNCTION:
            return term;

        case Term::INJECTIVE_FUNCTION:
            return m_dag.injective_function(name, approximate(arg0));

        case Term::BINARY_FUNCTION:
            return m_dag.binary_function(name, approximate(arg0),
                                         approximate(arg1));

        case Term::SYMMETRIC_FUNCTION:
            return m_dag.symmetric_function(name, approximate(arg0),
                                            approximate(arg1));

        case Term::UNARY_RELATION:
            return m_dag.unary_relation(name, approximate(arg0));

        case Term::BINARY_RELATION:
            return m_dag.binary_relation(name, approximate(arg0),
                                         approximate(arg1));

        case Term::VARIABLE:
            size_t &temp_depth = m_temp_depths[term];
            if (temp_depth == m_temp_max_depth) {
                return m_dag.hole();
            } else {
                auto i = m_definitions.find(term);
                if (i == m_definitions.end()) {
                    return m_dag.hole();
                } else {
                    ++temp_depth;
                    const Term *result = approximate(i->second);
                    --temp_depth;
                    return result;
                }
            }
    }

    POMAGMA_ERROR("unreachable");
}

//----------------------------------------------------------------------------
// Corpus

Corpus::Corpus(Signature &signature)
    : m_signature(signature), m_dag(*new Dag(signature)) {}

Corpus::~Corpus() { delete &m_dag; }

Corpus::Linker Corpus::linker(
    const std::vector<Corpus::LineOf<std::string>> &lines,
    std::vector<std::string> &error_log) {
    Parser parser(m_signature, m_dag, error_log);
    Linker linker(m_dag, error_log);
    for (const auto &line : lines) {
        if (line.has_name()) {
            const std::string &name = line.maybe_name;
            const Term *term = parser.parse(line.body);
            linker.define(name, term);
        }
    }
    linker.finish();
    return linker;
}

std::vector<Corpus::LineOf<const Corpus::Term *>> Corpus::parse(
    const std::vector<Corpus::LineOf<std::string>> &lines,
    Corpus::Linker &linker, std::vector<std::string> &error_log) {
    Parser parser(m_signature, m_dag, error_log);
    std::vector<LineOf<const Term *>> parsed;
    for (const auto &line : lines) {
        const Term *term = parser.parse(line.body);
        const Term *linked = linker.link(term);
        parsed.push_back(LineOf<const Term *>({line.maybe_name, linked}));
    }
    return parsed;
}

const Corpus::Histogram &Corpus::histogram() const { return m_dag.histogram(); }

}  // namespace pomagma
