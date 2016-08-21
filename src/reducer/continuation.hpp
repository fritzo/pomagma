#pragma once

#include <pomagma/reducer/util.hpp>
#include <pomagma/third_pary/farmhash/farmhash.h>
#include <pomagma/util/util.hpp>
#include <vector>

namespace pomagma {
namespace reducer {

// ---------------------------------------------------------------------------
// Code

struct Code : noncopyable {
    virtual ~Code() = default;
    virtual uint64_t hash() const = 0;

    const Code* app(const Code* lhs, const Code* rhs);
    const Code* join(const std::vector<Code*> terms);
    const Code* quote(const Code* arg);
    const Code* ivar(const uint32_t rank);
    const Code* abs(const Code* body);
    const Code* atom_TOP();
    const Code* atom_I();
    const Code* atom_K();
    const Code* atom_B();
    const Code* atom_C();
    const Code* atom_S();
    const Code* atom_EVAL();
    const Code* atom_LESS();
};

struct CodeApp : public Code {
    ~CodeApp override = default;
    uint64_t hash() const override {
        return util::Hash128to64(Uint128(reinterpret_cast<uint64_t>(lhs),
                                         reinterpret_cast<uint64_t>(rhs)));
    }

    const Code* const lhs;
    const Code* const rhs;
};

struct CodeJoin : public Code {
    ~CodeJoin() override = default;
    uint64_t hash() const override {
        return util::Hash64(static_cast<const char*>(terms.data()),
                            sizeof(const Code*) * terms.size());
    }

    const std::vector<const Code*> terms;
};

struct CodeQuote : public Code {
    ~CodeQuote() override = default;
    uint64_t hash() const override {
        return util::Hash64(reinterpret_cast<uint64_t>(arg));
    }

    const Code* const arg;
};

struct CodeIvar : public Code {
    ~CodeIvar() override = default;
    uint64_t hash() const override {
        return util::Hash64(static_cast<const char*>(&rank), sizeof(uint32_t));
    }

    const uint32_t rank;
};

struct CodeAbs : public Code {
    ~CodeAbs override = default;
    uint64_t hash() const override {
        return util::Hash64(reinterpret_cast<uint64_t>(arg));
    }

    const Code* const body;
};

struct CodeAtom : public Code {
    ~CodeAtom override = default;

    const std::string name;
};

// ---------------------------------------------------------------------------
// Cons hashing

struct HashCode {
    uint64_t operator()(const Code& code) const { return code.hash(); }
};

class CodeBuilder {
   public:
   private:
    static UniqueSet<Code> codes_;
};

// namespace reducer
// namespace pomagma
