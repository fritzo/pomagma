#include "hypothesize.hpp"
#include "consistency.hpp"
#include <pomagma/atlas/macro/binary_relation.hpp>
#include <pomagma/atlas/macro/compact.hpp>
#include <pomagma/atlas/macro/router.hpp>
#include <pomagma/atlas/macro/scheduler.hpp>
#include <cstdlib>
#include <unistd.h> // for fork
#include <sys/wait.h> // for wait

namespace pomagma
{

namespace detail
{

inline std::string tempfile_name (pid_t pid)
{
    std::ostringstream filename;
    filename << "/tmp/pomagma.hypothesize." << pid;
    return filename.str();
}

template<class T>
inline void tempfile_dump (pid_t pid, const T & t)
{
    std::string filename = tempfile_name(pid);
    std::ofstream file(filename.c_str(), std::ios::out | std::ios::trunc);
    POMAGMA_ASSERT(file, "failed to open tempfile " << filename);
    file << t << std::endl;
}

template<class T>
inline void tempfile_load (pid_t pid, T & t)
{
    std::string filename = tempfile_name(pid);
    {
        std::ifstream file(filename.c_str(), std::ios::in);
        POMAGMA_ASSERT(file, "failed to open tempfile " << filename);
        file >> t;
    }
    remove(filename.c_str());
}

void merge_if_consistent (
        Structure & structure,
        const std::pair<Ob, Ob> & equation)
{
    // TODO omit binary relation LESS
    //structure.signature().binary_relations().erase("LESS");

    configure_scheduler_to_merge_if_consistent(structure);
    structure.carrier().ensure_equal(equation.first, equation.second);
    process_mergers(structure.signature());
    compact(structure);
}

} // namespace detail

float hypothesize_entropy (
        Structure & structure,
        const std::unordered_map<std::string, float> & language,
        const std::pair<Ob, Ob> & equation,
        float reltol)
{
    POMAGMA_ASSERT_LT(0, reltol);
    POMAGMA_ASSERT_LT(reltol, 1);

    pid_t child = fork();
    POMAGMA_ASSERT(child != -1, "fork failed");
    if (child == 0) {

        POMAGMA_DEBUG("assuming equation");
        detail::merge_if_consistent(structure, equation);

        POMAGMA_DEBUG("measuring entropy");
        Router router(structure.signature(), language);
        const std::vector<float> probs = router.measure_probs(reltol);
        float entropy = get_entropy(probs);
        detail::tempfile_dump(getpid(), entropy);
        _exit(EXIT_CONSISTENT);

    } else {

        int status;
        POMAGMA_DEBUG("Waiting for child process " << child);
        waitpid(child, &status, 0);
        POMAGMA_ASSERT(WIFEXITED(status),
            "child process failed with status " << status);
        int info = WEXITSTATUS(status);

        float entropy = NAN;
        switch (info) {
            case EXIT_CONSISTENT:
                detail::tempfile_load(child, entropy);
                break;

            case EXIT_INCONSISTENT:
                entropy = 0.0;
                break;

            default:
                POMAGMA_ERROR("child process failed with code " << info);
        }

        return entropy;
    }
}

} // namespace pomagma
