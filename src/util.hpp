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

#ifndef POMAGMA_DEBUG_LEVEL
#define POMAGMA_DEBUG_LEVEL 0
#endif // POMAGMA_DEBUG_LEVEL

#define POMAGMA_ERROR(mess) {logger.error()\
    << mess << "\n\t"\
    << __FILE__ << " : " << __LINE__ << "\n\t"\
    << __PRETTY_FUNCTION__ << "\n" |0;\
    abort();}

#define POMAGMA_ASSERT(level, cond, mess) \
    { if ((level) >= POMAGMA_DEBUG_LEVEL and not (cond)) POMAGMA_ERROR(mess); }

namespace pomagma
{

//time & resources
float get_elapsed_time ();
std::string get_date (bool hour=true);

//================================ convenience ================================

typedef uint32_t oid_t;

template<class T> inline T min (T x, T y) { return (x < y) ? x : y; }
template<class T> inline T max (T x, T y) { return (x > y) ? x : y; }

//this is used with template specialization
template <class T> inline const char* nameof () { return "???"; }

//================================ logging ================================

namespace Logging
{

extern std::ofstream g_log_file;

class fake_ostream
{
    const bool m_live;
public:
    fake_ostream (bool live) : m_live(live) {}
    template <class Message>
    const fake_ostream& operator<< (const Message& message) const
    {
        if (m_live) { g_log_file << message; }
        return *this;
    }
    const fake_ostream& operator| (int hold) const
    {
        if (m_live) {
            if (hold)   g_log_file << std::flush; // log << ... |1; flushes
            else        g_log_file << std::endl;  // log << ... |0; ends line
        }
        return *this;
    }
};

const fake_ostream live_out(true), dead_out(false);

//title/section label
void title (std::string name);

//log channels
enum LogLevel {ERROR, WARNING, INFO, DEBUG};
class Logger
{
private:
    const std::string m_name;
    const LogLevel m_level;
public:
    Logger (std::string name, LogLevel level = INFO);
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

} // namespace Logging

using Logging::logger;

} // namespace pomagma

#endif

