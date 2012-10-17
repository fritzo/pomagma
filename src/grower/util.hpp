#pragma once

#include <stdint.h>
#include <cstdlib> // for exit() & abort();
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>
#include <iomanip>
#include <atomic>
#include <chrono>

namespace pomagma_messaging {}

namespace pomagma
{

// rename pomagma_messaging to pomagma::messaging
namespace messaging { using namespace pomagma_messaging; }

//----------------------------------------------------------------------------
// Compiler-specific

//#ifndef __STDC_VERSION__
//#  warning "__STDC_VERSION__ was undefined"
//#  define __STDC_VERSION__ 199901L
//#endif // __STDC_VERSION__

#ifndef restrict
#  ifdef __GNUG__
#    define restrict __restrict__
#  else // __GNUG__
#    warning "ignoring keyword 'restrict'"
#    define restrict
#  endif // __GNUG__
#endif // restrict

#ifdef __GNUG__
#  define likely(x) __builtin_expect(bool(x), true)
#  define unlikely(x) __builtin_expect(bool(x), false)
#else // __GNUG__
#  warning "ignoring likely(-), unlikely(-)"
#  define likely(x) (x)
#  define unlikely(x) (x)
#endif // __GNUG__

//----------------------------------------------------------------------------
// Debugging

#ifndef POMAGMA_DEBUG_LEVEL
#  define POMAGMA_DEBUG_LEVEL 0
#endif // POMAGMA_DEBUG_LEVEL

//----------------------------------------------------------------------------
// Convenience

template<class T> inline T min (T x, T y) { return (x < y) ? x : y; }
template<class T> inline T max (T x, T y) { return (x > y) ? x : y; }

// TODO switch to std::random_uniform_distribution<float>, etc.

inline size_t random_int (size_t LB, size_t UB)
{
    return LB + lrand48() % (UB - LB);
}

inline bool random_bool (double prob)
{
    return drand48() < prob;
}

inline double random_01 ()
{
    return drand48();
}

template<size_t x> struct static_log2i
{
    static size_t val () { return 1 + static_log2i<x / 2>::val(); };
};
template<> struct static_log2i<1>
{
    static size_t val () { return 0; };
};

float get_elapsed_time ();
std::string get_date (bool hour=true);

class Timer
{
    typedef std::chrono::high_resolution_clock Clock;
    typedef std::chrono::time_point<Clock> Time;
    Time m_start;
public:
    Timer () : m_start(Clock::now()) {}
    double elapsed () const
    {
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
                Clock::now() - m_start);
        return duration.count() * 1e-6;
    }
};

class Stopwatch
{
    typedef std::chrono::high_resolution_clock Clock;
    typedef std::chrono::time_point<Clock> Time;
    Time m_stop;
public:
    Stopwatch (std::chrono::milliseconds dt) : m_stop(Clock::now() + dt) {}
    bool done () const { return Clock::now() >= m_stop; }
    bool ok () const { return Clock::now() < m_stop; }
};

class noncopyable
{
    noncopyable (const noncopyable &) = delete;
    void operator= (const noncopyable &) = delete;
public:
    noncopyable () {}
};

#define POMAGMA_FOR(POMAGMA_type, POMAGMA_var, POMAGMA_init) \
    for (POMAGMA_type POMAGMA_var POMAGMA_init; \
         POMAGMA_var.ok(); \
         POMAGMA_var.next())

//----------------------------------------------------------------------------
// Logging

const std::string g_log_level_name[4] =
{
    "\e[7;31merror   \e[0;39m",  // error   - reverse red
    "\e[31mwarning \e[0;39m",    // warning - red
    "\e[32minfo    \e[0;39m",    // info    - green
    "\e[33mdebug   \e[0;39m"     // debug   - yellow
};

class Log
{
    static const char * s_log_filename;
    static std::ofstream s_log_stream;
    static const unsigned s_log_level;

    std::ostringstream m_message;

public:

    static unsigned level () { return s_log_level; }

    Log (unsigned level)
    {
        m_message << std::left << std::setw(12) << get_elapsed_time();
        m_message << g_log_level_name[min(4u, level)];
    }

    ~Log ()
    {
        m_message << std::endl;
        s_log_stream << m_message.str() << std::flush;
        std::cerr << m_message.str() << std::flush; // DEBUG
    }

    template<class T> Log & operator<< (const T & t)
    {
        m_message << t;
        return * this;
    }

    static void title (std::string name)
    {
        std::ostringstream message;
        message
            << "\e[32m" // green
            << name << " " << get_date()
            << "\e[0;39m"
            << std::endl;
        s_log_stream << message.str() << std::flush;
        std::cerr << message.str() << std::flush; // DEBUG
    }
};

#define POMAGMA_WARN(message) \
    { if (pomagma::Log::level() >= 1) { pomagma::Log(1) << message; } }
#define POMAGMA_INFO(message) \
    { if (pomagma::Log::level() >= 2) { pomagma::Log(2) << message; } }
#define POMAGMA_DEBUG(message) \
    { if (pomagma::Log::level() >= 3) { pomagma::Log(3) << message; } }

#define POMAGMA_ERROR(message) { pomagma::Log(0) \
    << message << "\n\t" \
    << __FILE__ << " : " << __LINE__ << "\n\t" \
    << __PRETTY_FUNCTION__ << "\n"; \
    abort(); }

#define TODO(message) POMAGMA_ERROR("TODO " << message)

#define POMAGMA_ASSERT(cond, mess) { if (not (cond)) POMAGMA_ERROR(mess) }

#define POMAGMA_ASSERT_(level, cond, mess) \
    { if (POMAGMA_DEBUG_LEVEL >= (level)) POMAGMA_ASSERT(cond, mess) }

#define POMAGMA_ASSERT1(cond, mess) POMAGMA_ASSERT_(1, cond, mess)
#define POMAGMA_ASSERT2(cond, mess) POMAGMA_ASSERT_(2, cond, mess)
#define POMAGMA_ASSERT3(cond, mess) POMAGMA_ASSERT_(3, cond, mess)
#define POMAGMA_ASSERT4(cond, mess) POMAGMA_ASSERT_(4, cond, mess)
#define POMAGMA_ASSERT5(cond, mess) POMAGMA_ASSERT_(5, cond, mess)
#define POMAGMA_ASSERT6(cond, mess) POMAGMA_ASSERT_(6, cond, mess)

#define POMAGMA_ASSERT_EQ(x, y) \
    POMAGMA_ASSERT((x) == (y), \
            "expected " #x " == " #y "; actual " << (x) << " vs " << (y))
#define POMAGMA_ASSERT_LE(x, y) \
    POMAGMA_ASSERT((x) <= (y), \
            "expected " #x " <= " #y "; actual " << (x) << " vs " << (y))
#define POMAGMA_ASSERT_LT(x, y) \
    POMAGMA_ASSERT((x) <= (y), \
            "expected " #x " <= " #y "; actual " << (x) << " vs " << (y))

#define POMAGMA_ASSERT_OK \
    POMAGMA_ASSERT5(ok(), "tried to use done iterator")

#define POMAGMA_ASSERT_CONTAINS3(POMAGMA_set, POMAGMA_x, POMAGMA_y, POMAGMA_z)\
    POMAGMA_ASSERT(POMAGMA_set.contains(POMAGMA_x, POMAGMA_y, POMAGMA_z),\
    #POMAGMA_set " is missing " #POMAGMA_x ", " #POMAGMA_y ", " #POMAGMA_z)

#define POMAGMA_ASSERT_RANGE_(POMAGMA_level, POMAGMA_i, POMAGMA_dim)\
    POMAGMA_ASSERT_(POMAGMA_level,\
        1 <= (POMAGMA_i) and (POMAGMA_i) <= (POMAGMA_dim),\
        "out of range: " #POMAGMA_i " = " << (POMAGMA_i))

#define POMAGMA_ASSERT_ALIGNED_(POMAGMA_level, POMAGMA_ptr)\
    POMAGMA_ASSERT_(\
        (POMAGMA_level),\
        (reinterpret_cast<size_t>(POMAGMA_ptr) & size_t(31)) == 0,\
        "bad alignment for variable " #POMAGMA_ptr)

//----------------------------------------------------------------------------
// Data types

// Ob is a 1-based index type with 0 = none
typedef uint16_t Ob;
const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;
static_assert(sizeof(Ob) == sizeof(std::atomic<Ob>),
        "std::atomic<Ob> is larger than Ob");

const size_t BITS_PER_CACHE_LINE = 512;
const size_t DEFAULT_ITEM_DIM = BITS_PER_CACHE_LINE - 1; // for one-based sets

//----------------------------------------------------------------------------
// Words of bits

typedef uint64_t Word;
const size_t BITS_PER_WORD = 8 * sizeof(Word);
const size_t WORD_POS_MASK = BITS_PER_WORD - 1;
const size_t WORD_POS_SHIFT = static_log2i<BITS_PER_WORD>::val();
const Word FULL_WORD = ~Word(0);
static_assert(FULL_WORD + Word(1) == 0, "FULL_WORD is bad");

//----------------------------------------------------------------------------
// Blocks of atomic Ob

const size_t LOG2_ITEMS_PER_BLOCK = 3;
const size_t ITEMS_PER_BLOCK = 1 << LOG2_ITEMS_PER_BLOCK;
const size_t BLOCK_POS_MASK = ITEMS_PER_BLOCK - 1;
typedef std::atomic<Ob> Block[ITEMS_PER_BLOCK * ITEMS_PER_BLOCK];

inline std::atomic<Ob> & _block2value (std::atomic<Ob> * block, Ob i, Ob j)
{
    POMAGMA_ASSERT6(i < ITEMS_PER_BLOCK, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_BLOCK, "out of range " << j);
    return block[(j << LOG2_ITEMS_PER_BLOCK) | i];
}

inline Ob _block2value (const std::atomic<Ob> * block, Ob i, Ob j)
{
    POMAGMA_ASSERT6(i < ITEMS_PER_BLOCK, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_BLOCK, "out of range " << j);
    return block[(j << LOG2_ITEMS_PER_BLOCK) | i];
}

} // namespace pomagma
