#pragma once

#include <algorithm>
#include <map>
#include <pomagma/util/aligned_alloc.hpp>
#include <pomagma/util/profiler.hpp>
#include <vector>

namespace pomagma {
class Signature;
namespace vm {

enum OpCode : uint8_t;
enum OpArgType : uint8_t;

// Thread local context
template <class Ob, class SetPtr>
struct Context_ {
    Ob obs[256];
    const SetPtr* sets[256];
    size_t block;
    size_t trace;
    ProgramProfiler profiler;
    LineProfiler line_profiler;

    void clear() {
        std::fill(std::begin(obs), std::end(obs), 0);
        std::fill(std::begin(sets), std::end(sets), nullptr);
        block = 0;
        trace = 0;
    }
} __attribute__((aligned(64)));

typedef const uint8_t* Program;
struct Listing {
    uint32_t program_offset;
    uint32_t size;
    uint32_t lineno;
};

class FileIndex {
   public:
    FileIndex() : m_offsets(1, 0) {}

    void add_file(const std::string& filename,
                  const std::vector<Listing>& listings);

    void save_stats(const std::vector<uint32_t>& histogram) const;

   private:
    // Parallel arrays:
    std::vector<std::string> m_filenames;
    std::vector<std::string> m_hexdigests;
    std::vector<size_t> m_sizes;
    std::vector<size_t> m_offsets;  // Has an extra starting 0 element

    void write_stats_file(
        const std::string& filepath,
        const std::map<uint32_t, uint64_t>& line_counts) const;
};

class ProgramParser {
   public:
    void load(Signature& signature);  // TODO input a proto, not Signature

    std::vector<Listing> parse(std::istream& infile);
    std::vector<Listing> parse_file(const std::string& filename);

    const std::vector<uint8_t>& programs() const { return m_program_data; }
    std::vector<uint32_t>& histogram() const { return m_histogram; }

    void save_line_profile_stats() const {
        m_file_index.save_stats(m_histogram);
    }

    // Calling parse() or parse_file() invalidates the returned Program.
    Program find_program(const Listing& listing) const {
        POMAGMA_ASSERT_LE(listing.program_offset + listing.size,
                          m_program_data.size());
        return m_program_data.data() + listing.program_offset;
    }

    template <class Ob, class SetPtr>
    void dump_continuation(Program program, const Context_<Ob, SetPtr>* context,
                           std::string& message);

    template <class Ob, class SetPtr>
    Program load_continuation(Context_<Ob, SetPtr>* context,
                              const std::string& message);

   private:
    const std::vector<uint8_t>& find_obs_used_by(size_t program_offset) {
        if (POMAGMA_DEBUG_LEVEL) {
            POMAGMA_ASSERT_LT(program_offset, m_program_data.size());
        }
        TODO("find which obs are used by a program");
    }

    std::vector<uint8_t> m_program_data;  // all programs in contiguous memory
    std::map<std::pair<OpArgType, std::string>, uint8_t> m_constants;
    mutable std::vector<uint32_t> m_histogram;  // same size as m_program_data
    FileIndex m_file_index;                     // tracks source locations

    class SymbolTable;
    class SymbolTableStack;
};

}  // namespace vm
}  // namespace pomagma
