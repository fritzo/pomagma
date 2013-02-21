#include <pomagma/util/util.hpp>
#include <sys/time.h>
#include <vector>

namespace pomagma
{

//----------------------------------------------------------------------------
// logging

const char * Log::s_log_filename =
    getenv_default("POMAGMA_LOG_FILE", DEFAULT_LOG_FILE);
std::ofstream Log::s_log_stream(s_log_filename, std::ios_base::app);

const size_t Log::s_log_level(
    getenv_default("POMAGMA_LOG_LEVEL", DEFAULT_LOG_LEVEL));

//----------------------------------------------------------------------------
// time

timeval g_begin_time;
const int g_init_time __attribute__((unused)) (gettimeofday(&g_begin_time, nullptr));
float get_elapsed_time ()
{
    timeval current_time;
    gettimeofday(& current_time, nullptr);
    return current_time.tv_sec - g_begin_time.tv_sec +
        (current_time.tv_usec - g_begin_time.tv_usec) * 1e-6;
}

std::string get_date (bool hour)
{
    const size_t size = 20; // fits e.g. 2007:05:17:11:33
    static char buff[size];

    time_t t = time(nullptr);
    tm T;
    gmtime_r (&t,&T);
    if (hour) strftime(buff,size, "%Y:%m:%d:%H:%M", &T);
    else      strftime(buff,size, "%Y:%m:%d", &T);
    return buff;
}

} // namespace pomagma
