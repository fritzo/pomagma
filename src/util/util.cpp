#include <sys/resource.h>
#include <sys/time.h>

#include <pomagma/util/util.hpp>
#include <vector>

namespace pomagma {

//----------------------------------------------------------------------------
// convenience

void util_static_tests() {
    // static_log2i
    static_assert(static_log2i<1>::val() == 0, "error");
    static_assert(static_log2i<2>::val() == 1, "error");
    static_assert(static_log2i<3>::val() == 1, "error");
    static_assert(static_log2i<4>::val() == 2, "error");
    static_assert(static_log2i<5>::val() == 2, "error");
    static_assert(static_log2i<6>::val() == 2, "error");
    static_assert(static_log2i<7>::val() == 2, "error");
    static_assert(static_log2i<8>::val() == 3, "error");
    static_assert(static_log2i<9>::val() == 3, "error");

    // static_power_of_two_padding
    static_assert(static_power_of_two_padding<1>::val() == 0, "error");
    static_assert(static_power_of_two_padding<3>::val() == 1, "error");
    static_assert(static_power_of_two_padding<5>::val() == 3, "error");
    static_assert(static_power_of_two_padding<6>::val() == 2, "error");
    static_assert(static_power_of_two_padding<7>::val() == 1, "error");
    static_assert(static_power_of_two_padding<9>::val() == 7, "error");
    static_assert(static_power_of_two_padding<10>::val() == 6, "error");
    static_assert(static_power_of_two_padding<11>::val() == 5, "error");
    static_assert(static_power_of_two_padding<12>::val() == 4, "error");
    static_assert(static_power_of_two_padding<13>::val() == 3, "error");
    static_assert(static_power_of_two_padding<14>::val() == 2, "error");
    static_assert(static_power_of_two_padding<15>::val() == 1, "error");

    // is_power_of_two
    static_assert(is_power_of_two(1), "error");
    static_assert(is_power_of_two(2), "error");
    static_assert(is_power_of_two(4), "error");
    static_assert(is_power_of_two(8), "error");
    static_assert(not is_power_of_two(3), "error");
    static_assert(not is_power_of_two(5), "error");
    static_assert(not is_power_of_two(6), "error");
    static_assert(not is_power_of_two(7), "error");
}

//----------------------------------------------------------------------------
// file system

void in_temp_dir(std::function<void()> body) {
    const auto old_path = fs::current_path();
    const auto temp_path =
        fs::unique_path("/tmp/pomagma.temp.%%%%-%%%%-%%%%-%%%%");
    POMAGMA_ASSERT(fs::create_directories(temp_path),
                   "failed to create temp directory");
    fs::current_path(temp_path);
    body();
    fs::current_path(old_path);
    fs::remove_all(temp_path);
}

//----------------------------------------------------------------------------
// logging

int Log::init() {
    std::ostringstream message;
    message << "----------------------------------------"
               "----------------------------------------"
               "\n"
            << get_date() << "\n";
    s_state.write(message.str());
    return 0;
}

Log::GlobalState::GlobalState()
    : log_filename(getenv_default("POMAGMA_LOG_FILE", DEFAULT_LOG_FILE)),
      log_stream(log_filename, std::ios_base::app),
      log_level(getenv_default("POMAGMA_LOG_LEVEL", DEFAULT_LOG_LEVEL)) {
    Log::init();
}

Log::GlobalState::~GlobalState() {
    for (const auto& callback : callbacks) {
        callback();
    }
}

Log::GlobalState Log::s_state;

Log::Context::Context(std::string name) {
    std::ostringstream message;
    message << name << '\n';
    s_state.write(message.str());
}

Log::Context::Context(int argc, char** argv) {
    std::ostringstream message;
    for (int i = 0; i < argc; ++i) {
        message << argv[i] << ' ';
    }
    message << '\n';
    s_state.write(message.str());
}

inline std::ostream& operator<<(std::ostream& o, const timeval& t) {
    return o << t.tv_sec << '.' << std::setfill('0') << std::setw(6)
             << t.tv_usec;
}

Log::Context::~Context() {
    rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    std::ostringstream message;
    message << "rusage.ru_utime = " << usage.ru_utime << "\n"
            << "rusage.ru_stime = " << usage.ru_stime << "\n"
            << "rusage.ru_maxrss = " << usage.ru_maxrss << "\n";
    s_state.write(message.str());
}

//----------------------------------------------------------------------------
// time

timeval g_begin_time;
const int g_init_time
    __attribute__((unused)) (gettimeofday(&g_begin_time, nullptr));
float get_elapsed_time() {
    timeval current_time;
    gettimeofday(&current_time, nullptr);
    return current_time.tv_sec - g_begin_time.tv_sec +
           (current_time.tv_usec - g_begin_time.tv_usec) * 1e-6;
}

std::string get_date(bool hour) {
    const size_t size = 20;  // fits e.g. 2007:05:17:11:33
    static char buff[size];

    time_t t = time(nullptr);
    tm T;
    gmtime_r(&t, &T);
    if (hour)
        strftime(buff, size, "%Y:%m:%d:%H:%M", &T);
    else
        strftime(buff, size, "%Y:%m:%d", &T);
    return buff;
}

}  // namespace pomagma
