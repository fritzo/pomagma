#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/atlas/signature.hpp>
#include <tuple>

namespace pomagma {

// TermParser parses terms but not statements
template <class Reducer>
class TermParser {
   public:
    // TermParser agrees not to touch reducer until after construction
    TermParser(Signature& signature, Reducer& reducer)
        : m_signature(signature), m_reducer(reducer) {}

    typedef typename Reducer::Term Term;
    Term parse(const std::string& expression) {
        begin(expression);
        Term result = parse_term();
        end();
        return result;
    }

    void begin(const std::string& expression) {
        m_stream.str(expression);
        m_stream.clear();
    }

    std::string parse_token() {
        std::string token;
        POMAGMA_ASSERT(std::getline(m_stream, token, ' '),
                       "expression terminated prematurely: " << m_stream.str());
        return token;
    }

    Term parse_term() {
        std::string token = parse_token();
        if (const auto* fun = m_signature.nullary_function(token)) {
            return m_reducer.reduce(token, fun);
        } else if (const auto* fun = m_signature.injective_function(token)) {
            Term key = parse_term();
            return m_reducer.reduce(token, fun, key);
        } else if (const auto* fun = m_signature.binary_function(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, fun, lhs, rhs);
        } else if (const auto* fun = m_signature.symmetric_function(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, fun, lhs, rhs);
        } else {
            POMAGMA_ERROR("unrecognized token '" << token
                                                 << "' in:" << m_stream.str());
            // return Term();
        }
    }

    void end() {
        std::string token;
        POMAGMA_ASSERT(not std::getline(m_stream, token, ' '),
                       "unexpected token '" << token
                                            << "' in: " << m_stream.str());
    }

   private:
    Signature& m_signature;
    Reducer& m_reducer;
    std::istringstream m_stream;
};

// ExprParser parses terms and statements
template <class Reducer>
class ExprParser {
   public:
    // ExprParser agrees not to touch reducer until after construction
    // ExprParser agrees not to touch error_log until after construction
    ExprParser(Signature& signature, Reducer& reducer,
               std::vector<std::string>& error_log)
        : m_signature(signature), m_reducer(reducer), m_error_log(error_log) {}

    typedef typename Reducer::Term Term;
    Term parse(const std::string& expression) {
        begin(expression);
        Term result = parse_term();
        end();
        return result;
    }

   private:
#define POMAGMA_PARSER_WARN(ARG_message)      \
    {                                         \
        std::ostringstream message;           \
        message << ARG_message;               \
        m_error_log.push_back(message.str()); \
        POMAGMA_WARN(message.str());          \
    }

    void begin(const std::string& expression) {
        m_stream.str(expression);
        m_stream.clear();
    }

    std::string parse_token() {
        std::string token;
        if (not std::getline(m_stream, token, ' ')) {
            POMAGMA_PARSER_WARN(
                "expression terminated prematurely: " << m_stream.str());
        }
        return token;
    }

    Term parse_term() {
        std::string token = parse_token();
        if (const auto* fun = m_signature.nullary_function(token)) {
            return m_reducer.reduce(token, fun);
        } else if (const auto* fun = m_signature.injective_function(token)) {
            Term key = parse_term();
            return m_reducer.reduce(token, fun, key);
        } else if (const auto* fun = m_signature.binary_function(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, fun, lhs, rhs);
        } else if (const auto* fun = m_signature.symmetric_function(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, fun, lhs, rhs);
        } else if (const auto* rel = m_signature.unary_relation(token)) {
            Term arg = parse_term();
            return m_reducer.reduce(token, rel, arg);
        } else if (const auto* rel = m_signature.binary_relation(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, rel, lhs, rhs);
        } else if (token == "EQUAL") {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce_equal(lhs, rhs);
        } else if (token == "HOLE") {
            return m_reducer.reduce_hole();
        } else if (token == "VAR") {
            std::string name = parse_token();
            return m_reducer.reduce_var(name);
        } else {
            POMAGMA_PARSER_WARN("unrecognized token '"
                                << token << "' in:" << m_stream.str());
            return m_reducer.reduce_error(token);
        }
    }

    void end() {
        std::string token;
        if (std::getline(m_stream, token, ' ')) {
            POMAGMA_PARSER_WARN("unexpected token '"
                                << token << "' in: " << m_stream.str());
        }
    }

#undef POMAGMA_PARSER_WARN

    Signature& m_signature;
    Reducer& m_reducer;
    std::vector<std::string>& m_error_log;
    std::istringstream m_stream;
};

class LineParser {
   public:
    explicit LineParser(const char* filename) : m_file(filename) {
        POMAGMA_ASSERT(m_file, "failed to open " << filename);
        next();
    }

    bool ok() const { return not m_line.empty(); }

    const std::string& operator*() const { return m_line; }

    void next() {
        while (std::getline(m_file, m_line)) {
            if (not m_line.empty() and m_line[0] != '#') {
                return;
            }
        }
        m_line.clear();
    }

   private:
    std::ifstream m_file;
    std::string m_line;
};

}  // namespace pomagma
