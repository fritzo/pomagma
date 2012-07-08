
#include "util.hpp"
//#include <ctime>
#include <sys/time.h>
#include <vector>
#include <sys/resource.h> //for rusage
#include <unistd.h> //for isatty

namespace pomagma
{

//================================ logging ================================

namespace Logging
{

const char * log_filename = getenv("POMAGMA_LOGFILE")
                          ? getenv("POMAGMA_LOGFILE")
                          : "pomagma.log";

std::ofstream logFile(log_filename, std::ios_base::app);
void switch_to_log (std::string filename)
{
    logFile.close();
    logFile.open(filename.c_str(), std::ios_base::app);
    if (not logFile.is_open()) {
        logFile.open (log_filename, std::ios_base::app);
        logger.warning() << "could not open log file " << filename |0;
    }
}

//title/section label
void title (std::string name)
{
    live_out << "\033[32m================ "
             << name << " " << get_date()
             << " ================\033[37m" |0; // green
}

//indentation stuff
int indentLevel(0);

//time measurement
timeval g_begin_time;
const int g_init_time __attribute__((unused)) (gettimeofday(&g_begin_time, NULL));
inline float elapsed_time ()
{
    timeval current_time;
    gettimeofday(& current_time, NULL);
    return current_time.tv_sec - g_begin_time.tv_sec +
        (current_time.tv_usec - g_begin_time.tv_usec) * 1e-6;
}

//log channels
std::string fill_8 (std::string s)
{
    while (s.size() < 8) s.push_back(' ');
    return s;
}
Logger::Logger (std::string name, LogLevel level)
        : m_name(fill_8(name)), m_level(level)
{}
const std::string levelBeg[] =
{
    //these set the color, write the log level, and backspace to write over;
    //  this communicates the log level as color in ansi terminals,
    //  and as a std::string usable by grep and non-ansi terminals
    "\e[7;31merror   \e[8D",  // error   - reverse red
    "\e[31mwarning \e[8D",    // warning - red
    "\e[32minfo    \e[8D",    // info    - green
    "\e[33mdebug   \e[8D"     // debug   - yellow
};
const std::string levelEnd = "\e[0;39m";
const fake_ostream& Logger::active_log (LogLevel level) const
{
    return live_out << elapsed_time() << '\t'
                    << levelBeg[level] << m_name << levelEnd
                    << indentation();
}

}

//time
float get_elapsed_time () { return Logging::elapsed_time(); }
std::string get_date (bool hour)
{
    const size_t size = 20; //fits e.g. 2007:05:17:11:33
    static char buff[size];

    time_t t = time(NULL);
    tm T;
    gmtime_r (&t,&T);
    if (hour) strftime(buff,size, "%Y:%m:%d:%H:%M", &T);
    else      strftime(buff,size, "%Y:%m:%d", &T);
    return buff;
}

} // namespace pomagma
