#pragma once

#include <stdint.h>
#include <unistd.h>
#include <cstdlib>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>
#include <iomanip>
#include <chrono>
#include <random>
#include <functional>
#include <mutex>

// for demangle() below
#ifdef __GNUG__
#  include <cxxabi.h>
#  include <memory>
#endif  // __GNUG__

namespace pomagma_messaging {}

namespace pomagma
{

// rename pomagma_messaging to pomagma::messaging
namespace messaging { using namespace pomagma_messaging; }

//----------------------------------------------------------------------------
// compiler-specific

//#ifndef __STDC_VERSION__
//#  warning "__STDC_VERSION__ was undefined"
//#  define __STDC_VERSION__ 199901L
//#endif // __STDC_VERSION__

#ifdef __GNUG__
#  define GCC_VERSION (__GNUC__ * 10000 + __GNUC_MINOR__ * 100)
#else // __GNUG__
#  define GCC_VERSION 0
#endif // __GNUG__

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

#if defined(__GNUG__) && (GCC_VERSION < 40800)
#  define thread_local __thread
#endif //  defined(__GNUG__) && (GCC_VERSION < 40800)

//----------------------------------------------------------------------------
// debugging

#ifndef POMAGMA_DEBUG_LEVEL
#  define POMAGMA_DEBUG_LEVEL 0
#endif // POMAGMA_DEBUG_LEVEL

//----------------------------------------------------------------------------
// convenience

template<class T> inline T min (T x, T y) { return (x < y) ? x : y; }
template<class T> inline T max (T x, T y) { return (x > y) ? x : y; }

typedef std::default_random_engine rng_t;

template<size_t x> struct static_log2i
{
    static size_t val () { return 1 + static_log2i<x / 2>::val(); };
};
template<> struct static_log2i<1>
{
    static size_t val () { return 0; };
};

//----------------------------------------------------------------------------
// time

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
    unsigned long elapsed_us () const
    {
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
                Clock::now() - m_start);
        return duration.count();
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

//----------------------------------------------------------------------------
// environment variables

inline const char * getenv_default(const char * key, const char * default_val)
{
    const char * val = getenv(key);
    return val ? val : default_val;
}

inline size_t getenv_default (const char * key, size_t default_val)
{
    const char * val = getenv(key);
    return val ? atoi(val) : default_val;
}

inline int getenv_default (const char * key, int default_val)
{
    const char * val = getenv(key);
    return val ? atoi(val) : default_val;
}

inline float getenv_default (const char * key, float default_val)
{
    const char * val = getenv(key);
    return val ? atof(val) : default_val;
}

//----------------------------------------------------------------------------
// logging

const char * const DEFAULT_LOG_FILE = "pomagma.log";
const size_t DEFAULT_LOG_LEVEL = 1;

static const char * g_log_level_name[4] =
{
    "ERROR   ",
    "WARNING ",
    "INFO    ",
    "DEBUG   "
};

class Log
{
    struct GlobalState
    {
        const char * log_filename;
        std::ofstream log_stream;
        const size_t log_level;
        std::vector<std::function<void()>> callbacks;
        std::mutex mutex;

        GlobalState ();
        ~GlobalState ();

        void write (const std::string & message)
        {
            std::unique_lock<std::mutex> lock(mutex);
            s_state.log_stream << message << std::flush;
            //std::cerr << message << std::flush; // DEBUG
        }
    };

    static GlobalState s_state;

    std::ostringstream m_message;

public:

    static size_t level () { return s_state.log_level; }

    Log (size_t level)
    {
        m_message << std::left << std::setw(8) << getpid();
        m_message << std::left << std::setw(12) << get_elapsed_time();
        m_message << g_log_level_name[min<size_t>(3, level)];
    }

    ~Log ()
    {
        m_message << '\n';
        s_state.write(m_message.str());
    }

    template<class T> Log & operator<< (const T & t)
    {
        m_message << t;
        return * this;
    }

    struct Context
    {
        Context(std::string name);
        Context(int argc, char ** argv);
        ~Context();
    };

    static int init ();

    void on_exit (const std::function<void()> & callback)
    {
        s_state.callbacks.push_back(callback);
    }
};

#define POMAGMA_WARN(message) \
    { if (pomagma::Log::level() >= 1) { pomagma::Log(1) << message; } }
#define POMAGMA_INFO(message) \
    { if (pomagma::Log::level() >= 2) { pomagma::Log(2) << message; } }
#define POMAGMA_DEBUG(message) \
    { if (pomagma::Log::level() >= 3) { pomagma::Log(3) << message; } }

#define POMAGMA_PRINT(variable) POMAGMA_INFO(#variable " = " << (variable))

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
    POMAGMA_ASSERT((x) < (y), \
            "expected " #x " < " #y "; actual " << (x) << " vs " << (y))
#define POMAGMA_ASSERT_NE(x, y) \
    POMAGMA_ASSERT((x) != (y), \
            "expected " #x " != " #y "; actual " << (x) << " vs " << (y))

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
// data types

template<size_t bytes> struct uint_;
template<> struct uint_<1> { typedef uint8_t t; };
template<> struct uint_<2> { typedef uint16_t t; };
template<> struct uint_<4> { typedef uint32_t t; };
template<> struct uint_<8> { typedef uint64_t t; };

typedef size_t Word;
static const size_t BITS_PER_WORD = 8 * sizeof(Word);
static const size_t WORD_POS_MASK = BITS_PER_WORD - 1;
static const size_t WORD_POS_SHIFT = static_log2i<BITS_PER_WORD>::val();
static const Word FULL_WORD = ~Word(0);
static_assert(FULL_WORD + Word(1) == 0, "FULL_WORD is bad");

static const size_t BYTES_PER_CACHE_LINE = 64;
static const size_t BITS_PER_CACHE_LINE = 512;

//----------------------------------------------------------------------------
// iteration

template<class Iterator>
class Range
{
    const Iterator m_begin;
    const Iterator m_end;
public:
    Range (const Iterator & b, const Iterator & e) : m_begin(b), m_end(e) {}
    const Iterator & begin () const { return m_begin; }
    const Iterator & end () const { return m_end; }
};

template<class Iterator>
inline Range<Iterator> range (const Iterator & begin, const Iterator & end)
{
    return Range<Iterator>(begin, end);
}


//----------------------------------------------------------------------------
// vector operations

template<class T>
inline std::ostream & operator<< (std::ostream & o, const std::vector<T> & x)
{
    o << "[";
    if (not x.empty()) {
        o << x[0];
        for (size_t i = 1; i < x.size(); ++i) {
            o << ", " << x[i];
        }
    }
    return o << "]";
}

template<class T>
inline bool operator== (const std::vector<T> & x, const std::vector<T> & y)
{
    if (x.size() != y.size()) {
        return false;
    }
    for (size_t i = 0, I = x.size(); i != I; ++i) {
        if (x[i] != y[i]) {
            return false;
        }
    }
    return true;
}

//----------------------------------------------------------------------------
// map operations

template<class Map>
inline const typename Map::mapped_type & map_find (
        const Map & map,
        const typename Map::key_type & key)
{
    auto iter = map.find(key);
    POMAGMA_ASSERT(iter != map.end(), "missing key " << key);
    return iter->second;
}

template<class Map>
inline const typename Map::mapped_type & map_get (
        const Map & map,
        const typename Map::key_type & key,
        const typename Map::mapped_type & default_value)
{
    auto iter = map.find(key);
    if (iter != map.end()) {
        return iter->second;
    } else {
        return default_value;
    }
}

//----------------------------------------------------------------------------
// string operations

inline std::string get_filename (const std::string & path)
{
    size_t pos = path.find_last_of("/");
    if (pos != std::string::npos) {
        return std::string(path.begin() + pos + 1, path.end());
    } else {
        return path;
    }
}

// adapted from http://stackoverflow.com/questions/281818
#ifdef __GNUG__
inline std::string demangle (const char * name)
{
    int status = 0;
    std::unique_ptr<char, void(*)(void*)> result {
        abi::__cxa_demangle(name, NULL, NULL, &status),
        std::free
    };
    return (status == 0) ? result.get() : name;
}
#else  // __GNUG__
inline std::string demangle (const char * name)
{
    return name;
}
#endif  // __GNUG__

} // namespace pomagma
