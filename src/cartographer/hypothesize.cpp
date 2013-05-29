#include "hypothesize.hpp"
#include "binary_relation.hpp"
#include "compact.hpp"
#include "router.hpp"
#include "scheduler.hpp"
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

class ConsistencyChecker
{
public:

    ConsistencyChecker (Structure & structure)
        : m_carrier(structure.carrier()),
          m_nless(* structure.signature().binary_relations("NLESS"))
    {
    }

    bool check (Ob dep)
    {
        Ob rep = m_carrier.find(dep);
        POMAGMA_ASSERT_LT(rep, dep);
        return not (m_nless.find(dep, rep) or m_nless.find(rep, dep));
    }

public:

    Carrier & m_carrier;
    BinaryRelation & m_nless;
};

ConsistencyChecker * g_consistency_checker = nullptr;

static const int CONSISTENT = EXIT_SUCCESS;
static const int INCONSISTENT = EXIT_FAILURE;

void schedule_merge_if_consistent (Ob dep)
{
    if (likely(g_consistency_checker->check(dep))) {
        schedule_merge(dep);
    } else {
        POMAGMA_INFO("INCONSISTENT");
        _exit(INCONSISTENT);
    }
}

void merge_if_consistent (
        Structure & structure,
        const std::pair<Ob, Ob> & equation)
{
    // TODO omit binary relation LESS
    //structure.signature().binary_relations().erase("LESS");

    Ob dep = std::max(equation.first, equation.second);
    Ob rep = std::min(equation.first, equation.second);
    Carrier & carrier = structure.carrier();
    g_consistency_checker = new ConsistencyChecker(structure);
    carrier.set_merge_callback(schedule_merge);
    carrier.merge(dep, rep);
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
        Router router(structure, language);
        const std::vector<float> probs = router.measure_probs(reltol);
        float entropy = get_entropy(probs);
        detail::tempfile_dump(getpid(), entropy);
        _exit(detail::CONSISTENT);

    } else {

        int status;
        POMAGMA_DEBUG("Waiting for child process " << child);
        waitpid(child, &status, 0);
        POMAGMA_ASSERT(WIFEXITED(status),
            "child process failed with status " << status);
        int info = WEXITSTATUS(status);

        float entropy = NAN;
        switch (info) {
            case detail::CONSISTENT:
                detail::tempfile_load(child, entropy);
                break;

            case detail::INCONSISTENT:
                entropy = 0.0;
                break;

            default:
                POMAGMA_ERROR("child process failed with code " << info);
        }

        return entropy;
    }
}

} // namespace pomagma
