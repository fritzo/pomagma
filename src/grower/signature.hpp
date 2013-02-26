#pragma once

#include <pomagma/grower/util.hpp>

namespace pomagma
{

class Carrier;
class BinaryRelation;
class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

class Signature
{
public:

    struct Observer
    {
        Observer (Signature & signature);
        virtual void declare (const std::string &, BinaryRelation &) = 0;
        virtual void declare (const std::string &, NullaryFunction &) = 0;
        virtual void declare (const std::string &, InjectiveFunction &) = 0;
        virtual void declare (const std::string &, BinaryFunction &) = 0;
        virtual void declare (const std::string &, SymmetricFunction &) = 0;
    };

private:

    Carrier & m_carrier;
    std::vector<Observer *> m_observers;

    enum State { ADDING_OBSERVERS, DECLARING };
    State m_state;

    void add (Observer * observer)
    {
        POMAGMA_ASSERT(m_state == ADDING_OBSERVERS,
                "tried to add observer after declaring");
        m_observers.push_back(observer);
    }

public:

    Signature (Carrier & carrier)
        : m_carrier(carrier),
          m_state(ADDING_OBSERVERS)
    {}

    Carrier & carrier () { return m_carrier; }

    template<class T>
    void declare (const std::string & name, T & t)
    {
        for (auto o : m_observers) {
            o->declare(name, t);
        }
        m_state = DECLARING;
    }
};

inline Signature::Observer::Observer (Signature & signature)
{
    signature.add(this);
}

} // namespace pomagma
