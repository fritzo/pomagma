#ifndef POMAGMA_DEFINITIONS_H
#define POMAGMA_DEFINITIONS_H

#include <stdint.h>
#include <cstdlib> //for exit() & abort();
//#include <cstdio>
#include <iostream>
#include <string>
#include <sstream>
//#include <cassert>
//#include <cmath>
#include <fstream>

//============================ compiler-specific ============================

#ifndef __STDC_VERSION__
  #define __STDC_VERSION__ 199901L
#endif

#ifdef __GNUG__
  #define restrict __restrict__
#else
  #warning keyword 'restrict' ignored
  #define restrict
#endif

//================================ debugging ================================

#ifndef DEBUG_LEVEL
    #define DEBUG_LEVEL 0
    #define NDEBUG
#endif

#define POMAGMA_ERROR(mess) {logger.error()\
    << mess << "\n\t"\
    << __FILE__ << " : " << __LINE__ << "\n\t"\
    << __PRETTY_FUNCTION__ << "\n" |0;\
    abort();}

#define POMAGMA_ASSERT(cond,mess) {if (!(cond)) POMAGMA_ERROR(mess);}

//controlled assertions
#if DEBUG_LEVEL >= 1
  #define POMAGMA_ASSERT1(cond,mess) {POMAGMA_ASSERT(cond,mess)}
#else
  #define POMAGMA_ASSERT1(cond,mess)
#endif
#if DEBUG_LEVEL >= 2
  #define POMAGMA_ASSERT2(cond,mess) {POMAGMA_ASSERT(cond,mess)}
#else
  #define POMAGMA_ASSERT2(cond,mess)
#endif
#if DEBUG_LEVEL >= 3
  #define POMAGMA_ASSERT3(cond,mess) {POMAGMA_ASSERT(cond,mess)}
#else
  #define POMAGMA_ASSERT3(cond,mess)
#endif
#if DEBUG_LEVEL >= 4
  #define POMAGMA_ASSERT4(cond,mess) {POMAGMA_ASSERT(cond,mess)}
#else
  #define POMAGMA_ASSERT4(cond,mess)
#endif
#if DEBUG_LEVEL >= 5
  #define POMAGMA_ASSERT5(cond,mess) {POMAGMA_ASSERT(cond,mess)}
#else
  #define POMAGMA_ASSERT5(cond,mess)
#endif

//special assertions
#define POMAGMA_ASSERTW(cond,mess) {if (!(cond)) {logger.warning() << mess |0;}}

#define POMAGMA_ASSERTP(ptr,block_size,name) { \
    POMAGMA_ASSERT(ptr, "failed to allocate " << name); \
    POMAGMA_ASSERTW(0 == reinterpret_cast<size_t>(ptr) % block_size, \
            "bad alignment given to " << name); }

namespace pomagma
{

using std::cin;
using std::cout;
using std::endl;
using std::string;
using std::ostream;
using std::istream;
using std::fstream;
using std::ofstream;
using std::ifstream;

//time & resources
float get_elapsed_time ();
string get_date (bool hour=true);

//================================ convenience ================================

typedef uint32_t oid_t;

template<class T> inline T min (T x, T y) { return (x < y) ? x : y; }
template<class T> inline T max (T x, T y) { return (x > y) ? x : y; }

//this is used with template specialization
template <class T> inline const char* nameof () { return "???"; }

//================================ logging ================================

namespace Logging
{

extern ofstream logFile;
void switch_to_log (string filename);

class fake_ostream
{
    const bool m_live;
public:
    fake_ostream (bool live) : m_live(live) {}
    template <class Message>
    const fake_ostream& operator<< (const Message& message) const
    {
        if (m_live) { logFile << message; }
        return *this;
    }
    const fake_ostream& operator| (int hold) const
    {
        if (m_live) {
            if (hold)   logFile << std::flush; // log << ... |1; flushes
            else        logFile << std::endl;  // log << ... |0; ends line
        }
        return *this;
    }
};

const fake_ostream live_out(true), dead_out(false);

//title/section label
void title (string name);

//indentation stuff
const int length = 64;
const int stride = 2;
const char* const spaces = "                                                                " + length;
extern int indentLevel;
inline void indent ();
inline void outdent ();
inline const char* indentation ()
{ return spaces - min(length, indentLevel * stride); }
class IndentBlock
{
    bool m_active;
public:
    IndentBlock (bool active=true) : m_active(active)
    { if (m_active) indent (); }
    ~IndentBlock () { if (m_active) outdent (); }
};

//log channels
enum LogLevel {ERROR, WARNING, INFO, DEBUG};
class Logger
{
private:
    const string m_name;
    const LogLevel m_level;
public:
    Logger (string name, LogLevel level = INFO);
    const fake_ostream& active_log (LogLevel level) const;

    //status
    bool at_ (LogLevel level) const { return level <= m_level; }
    bool at_warning () const { return at_(WARNING); }
    bool at_info    () const { return at_(INFO); }
    bool at_debug   () const { return at_(DEBUG); }

    //heading
    void static heading (char* label);

    //log
    const fake_ostream& log (LogLevel level) const
    { return (level <= m_level) ? active_log(level) : dead_out; }
    const fake_ostream& error   () const { return log(ERROR); }
    const fake_ostream& warning () const { return log(WARNING); }
    const fake_ostream& info    () const { return log(INFO); }
    const fake_ostream& debug   () const { return log(DEBUG); }
};

const Logging::Logger logger("pomagma", Logging::INFO);

inline void indent ()
{
    ++indentLevel;
}
inline void outdent ()
{
    --indentLevel;
    POMAGMA_ASSERT1(indentLevel >= 0, "indent level underflow");
}

} // namespace Logging

using Logging::logger;

} // namespace pomagma

#endif

