#pragma once

#include "util.hpp"
#include <unordered_map>

namespace pomagma
{

class Carrier;
class BinaryRelation;
class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

// a shallow data structure managing opaque carrier, relations, and functions
class Signature : noncopyable
{
    Carrier * m_carrier;
    std::unordered_map<std::string, BinaryRelation *> m_binary_relations;
    std::unordered_map<std::string, NullaryFunction *> m_nullary_functions;
    std::unordered_map<std::string, InjectiveFunction *> m_injective_functions;
    std::unordered_map<std::string, BinaryFunction *> m_binary_functions;
    std::unordered_map<std::string, SymmetricFunction *> m_symmetric_functions;

public:

    Signature () : m_carrier(nullptr) {}

    void clear ();

    void declare (Carrier & carrier);
    void declare (const std::string & name, BinaryRelation & rel);
    void declare (const std::string & name, NullaryFunction & fun);
    void declare (const std::string & name, InjectiveFunction & fun);
    void declare (const std::string & name, BinaryFunction & fun);
    void declare (const std::string & name, SymmetricFunction & fun);

    Carrier * replace (Carrier & carrier);
    BinaryRelation * replace (const std::string & name, BinaryRelation &);
    NullaryFunction * replace (const std::string & name, NullaryFunction &);
    InjectiveFunction * replace (const std::string & name, InjectiveFunction &);
    BinaryFunction * replace (const std::string & name, BinaryFunction &);
    SymmetricFunction * replace (const std::string & name, SymmetricFunction &);

    Carrier * carrier () const { return m_carrier; }
    BinaryRelation * binary_relation (const std::string & name) const;
    NullaryFunction * nullary_function (const std::string & name) const;
    InjectiveFunction * injective_function (const std::string & name) const;
    BinaryFunction * binary_function (const std::string & name) const;
    SymmetricFunction * symmetric_function (const std::string & name) const;

    const std::unordered_map<std::string, BinaryRelation *> &
        binary_relations () const;
    const std::unordered_map<std::string, NullaryFunction *> &
        nullary_functions () const;
    const std::unordered_map<std::string, InjectiveFunction *> &
        injective_functions () const;
    const std::unordered_map<std::string, BinaryFunction *> &
        binary_functions () const;
    const std::unordered_map<std::string, SymmetricFunction *> &
        symmetric_functions () const;

    std::string negate (const std::string & name)
    {
        if (name == "LESS") return "NLESS";
        if (name == "NLESS") return "LESS";
        POMAGMA_ERROR("failed to negate name: " << name);
    }

private:

    template<class Function>
    static Function * find (
        const std::unordered_map<std::string, Function *> & funs,
        const std::string & key)
    {
        const auto & i = funs.find(key);
        return i == funs.end() ? nullptr : i->second;
    }
};

inline void Signature::clear ()
{
    m_binary_relations.clear();
    m_nullary_functions.clear();
    m_injective_functions.clear();
    m_binary_functions.clear();
    m_symmetric_functions.clear();
    m_carrier = nullptr;
}


inline void Signature::declare (
        Carrier & carrier)
{
    POMAGMA_ASSERT(m_carrier == nullptr, "Declared carrier twice");
    m_carrier = & carrier;
}

inline void Signature::declare (
        const std::string & name,
        BinaryRelation & rel)
{
    m_binary_relations.insert(std::make_pair(name, & rel));
}

inline void Signature::declare (
        const std::string & name,
        NullaryFunction & fun)
{
    m_nullary_functions.insert(std::make_pair(name, & fun));
}

inline void Signature::declare (
        const std::string & name,
        InjectiveFunction & fun)
{
    m_injective_functions.insert(std::make_pair(name, & fun));
}

inline void Signature::declare (
        const std::string & name,
        BinaryFunction & fun)
{
    m_binary_functions.insert(std::make_pair(name, & fun));
}

inline void Signature::declare (
        const std::string & name,
        SymmetricFunction & fun)
{
    m_symmetric_functions.insert(std::make_pair(name, & fun));
}


namespace detail
{
template<class T>
inline T * replace (T * & pointer, T * new_value)
{
    POMAGMA_ASSERT(pointer != nullptr, "nothing to replace");
    T * old_value = pointer;
    pointer = new_value;
    return old_value;
}
template<class T>
inline T * replace (
        std::unordered_map<std::string, T *> & map,
        const std::string & name,
        T * new_value)
{
    auto i = map.find(name);
    POMAGMA_ASSERT(i != map.end(), "nothing to replace");
    return replace(i->second, new_value);
}
} // namespace detail

inline Carrier * Signature::replace (
        Carrier & carrier)
{
    return detail::replace(m_carrier, & carrier);
}

inline BinaryRelation * Signature::replace (
        const std::string & name,
        BinaryRelation & rel)
{
    return detail::replace(m_binary_relations, name, & rel);
}

inline NullaryFunction * Signature::replace (
        const std::string & name,
        NullaryFunction & fun)
{
    return detail::replace(m_nullary_functions, name, & fun);
}

inline InjectiveFunction * Signature::replace (
        const std::string & name,
        InjectiveFunction & fun)
{
    return detail::replace(m_injective_functions, name, & fun);
}

inline BinaryFunction * Signature::replace (
        const std::string & name,
        BinaryFunction & fun)
{
    return detail::replace(m_binary_functions, name, & fun);
}

inline SymmetricFunction * Signature::replace (
        const std::string & name,
        SymmetricFunction & fun)
{
    return detail::replace(m_symmetric_functions, name, & fun);
}


inline BinaryRelation * Signature::binary_relation (
	const std::string & name) const
{
    return find(m_binary_relations, name);
}

inline NullaryFunction * Signature::nullary_function (
	const std::string & name) const
{
    return find(m_nullary_functions, name);
}

inline InjectiveFunction * Signature::injective_function (
	const std::string & name) const
{
    return find(m_injective_functions, name);
}

inline BinaryFunction * Signature::binary_function (
	const std::string & name) const
{
    return find(m_binary_functions, name);
}

inline SymmetricFunction * Signature::symmetric_function (
	const std::string & name) const
{
    return find(m_symmetric_functions, name);
}


inline const std::unordered_map<std::string, BinaryRelation *> &
Signature::binary_relations () const
{
    return m_binary_relations;
}

inline const std::unordered_map<std::string, NullaryFunction *> &
Signature::nullary_functions () const
{
    return m_nullary_functions;
}

inline const std::unordered_map<std::string, InjectiveFunction *> &
Signature::injective_functions () const
{
    return m_injective_functions;
}

inline const std::unordered_map<std::string, BinaryFunction *> &
Signature::binary_functions () const
{
    return m_binary_functions;
}

inline const std::unordered_map<std::string, SymmetricFunction *> &
Signature::symmetric_functions () const
{
    return m_symmetric_functions;
}

} // namespace pomagma
