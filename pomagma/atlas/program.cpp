#include "program.hpp"

#include <filesystem>
#include <fstream>
#include <map>
#include <pomagma/util/hasher.hpp>
#include <sstream>
#include <unordered_set>

#include "signature.hpp"

namespace pomagma {
namespace vm {

const std::string g_op_code_names[] = {
#define DO(X, Y) #X,
    POMAGMA_OP_CODES(DO)
#undef DO
};

const std::map<std::string, OpCode> g_op_codes = {
#define DO(X, Y) {#X, X},
    POMAGMA_OP_CODES(DO)
#undef DO
};

inline std::vector<std::vector<OpArgType>> get_op_code_arities() {
    std::vector<std::vector<OpArgType>> result = {
#define DO(X, Y) std::vector<OpArgType> Y,
        POMAGMA_OP_CODES(DO)
#undef DO
    };
    return result;
}

const std::vector<std::vector<OpArgType>> g_op_code_arities =
    get_op_code_arities();

class ProgramParser::SymbolTable {
    std::unordered_map<std::string, uint8_t> m_registers;
    std::unordered_set<std::string> m_loaded;

   public:
    uint8_t store(const std::string &name, size_t lineno) {
        POMAGMA_ASSERT(m_registers.find(name) == m_registers.end(),
                       "line " << lineno << ": duplicate variable: " << name);
        POMAGMA_ASSERT(
            m_registers.size() < 256,
            "line " << lineno << ": too many variables, limit = 256");

        uint8_t index = m_registers.size();
        m_registers.insert(std::make_pair(name, index));
        return index;
    }

    uint8_t load(const std::string &name, size_t lineno) {
        auto i = m_registers.find(name);
        POMAGMA_ASSERT(i != m_registers.end(),
                       "line " << lineno << ": undefined variable: " << name);
        m_loaded.insert(name);
        return i->second;
    }

    void check_unused(size_t lineno) const {
        for (const auto &pair : m_registers) {
            const std::string &name = pair.first;
            POMAGMA_ASSERT(m_loaded.find(name) != m_loaded.end(),
                           "line " << lineno << ": unused variable: " << name);
        }
    }
};

class ProgramParser::SymbolTableStack {
    std::vector<SymbolTable> m_stack;
    std::vector<size_t> m_jumps;
    const bool m_warn_unused;

   public:
    explicit SymbolTableStack(bool warn_unused) : m_warn_unused(warn_unused) {
        m_stack.resize(1);
    }

    uint8_t store(const std::string &name, size_t lineno) {
        return m_stack.back().store(name, lineno);
    }

    uint8_t load(const std::string &name, size_t lineno) {
        return m_stack.back().load(name, lineno);
    }

    void clear(size_t lineno) {
        POMAGMA_ASSERT(m_jumps.empty(), "line "
                                            << lineno
                                            << ": unterminated SEQUENCE command"
                                               ", len(jumps) = "
                                            << m_jumps.size());
        POMAGMA_ASSERT(m_stack.size() == 1,
                       "line " << lineno
                               << ": unterminated SEQUENCE command"
                                  ", len(stack) = "
                               << m_stack.size());
        if (m_warn_unused) {
            m_stack.back().check_unused(lineno);
        }
        m_stack.clear();
        m_stack.resize(1);
    }

    void push(uint8_t jump, size_t lineno) {
        POMAGMA_DEBUG("push vars at line " << lineno);
        m_stack.push_back(m_stack.back());
        m_jumps.push_back(eval_float53(jump));
    }

    void pop(size_t lineno) {
        for (auto &jump : m_jumps) {
            POMAGMA_ASSERT(jump, "programmer error");
            --jump;
        }
        if (not m_jumps.empty() and m_jumps.back() == 0) {
            POMAGMA_DEBUG("pop vars at line " << lineno);
            if (m_warn_unused) {
                m_stack.back().check_unused(lineno);
            }
            m_stack.pop_back();
            m_jumps.pop_back();
        }
    }
};

template <class Table>
static void declare(
    OpArgType arity, const std::unordered_map<std::string, Table *> &pointers,
    std::map<std::pair<OpArgType, std::string>, uint8_t> &symbols) {
    POMAGMA_ASSERT(pointers.size() <= 256,
                   "too many "
                   // << demangle(typeid(Table).name()) <<
                   " symbols: "
                   "expected <= 256, actual = "
                       << pointers.size());

    std::map<std::string, Table *> sorted;
    sorted.insert(pointers.begin(), pointers.end());
    uint8_t vm_pointer = 0;
    for (auto pair : sorted) {
        symbols[std::make_pair(arity, pair.first)] = vm_pointer++;
    }
}

void ProgramParser::load(Signature &signature) {
    m_program_data.clear();
    m_constants.clear();
    m_histogram.clear();
    declare(UNARY_RELATION, signature.unary_relations(), m_constants);
    declare(BINARY_RELATION, signature.binary_relations(), m_constants);
    declare(NULLARY_FUNCTION, signature.nullary_functions(), m_constants);
    declare(INJECTIVE_FUNCTION, signature.injective_functions(), m_constants);
    declare(BINARY_FUNCTION, signature.binary_functions(), m_constants);
    declare(SYMMETRIC_FUNCTION, signature.symmetric_functions(), m_constants);
}

std::vector<Listing> ProgramParser::parse_file(const std::string &filename) {
    POMAGMA_INFO("loading programs from " << filename);
    std::ifstream infile(filename, std::ifstream::in | std::ifstream::binary);
    POMAGMA_ASSERT(infile.is_open(), "failed to open file: " << filename);
    auto listings = parse(infile);
    m_file_index.add_file(filename, listings);
    return listings;
}

std::vector<Listing> ProgramParser::parse(std::istream &infile) {
    std::vector<Listing> result;
    std::vector<uint8_t> program;
    SymbolTableStack obs(false);
    SymbolTableStack sets(true);
    std::string line;
    std::string word;

    auto add_program = [&](size_t lineno) {
        Listing listing;
        listing.program_offset = m_program_data.size();
        listing.size = program.size();
        listing.lineno = lineno;
        result.push_back(listing);
        m_program_data.insert(m_program_data.end(), program.begin(),
                              program.end());
        m_histogram.resize(m_program_data.size());
        program.clear();
    };

    size_t start_lineno = 0;
    for (int lineno = 1; std::getline(infile, line); ++lineno) {
        if (line.size() and line[0] == '#') {
            continue;
        }
        if (line.empty()) {
            obs.clear(lineno);
            sets.clear(lineno);
            if (not program.empty()) {
                add_program(start_lineno);
            }
            continue;
        }
        if (program.empty()) {
            start_lineno = lineno;
        }

        std::istringstream stream(line);

        POMAGMA_ASSERT(stream >> word, "line " << lineno << ": no operation");
        obs.pop(lineno);
        sets.pop(lineno);
        auto i = g_op_codes.find(word);
        POMAGMA_ASSERT(i != g_op_codes.end(),
                       "line " << lineno << ": unknown operation: " << word);
        OpCode op_code = i->second;
        program.push_back(op_code);

        for (auto arg_type : g_op_code_arities[op_code]) {
            POMAGMA_ASSERT(stream >> word,
                           "line " << lineno << ": too few arguments");

            uint8_t arg = 0xff;
            switch (arg_type) {
                case UINT8: {
                    int uint8 = atoi(word.c_str());
                    POMAGMA_ASSERT(
                        (0 < uint8) and (uint8 < 255),
                        "line " << lineno << ": out of range: " << uint8);
                    arg = uint8;
                } break;

                case NEW_OB: {
                    arg = obs.store(word, lineno);
                } break;
                case OB: {
                    arg = obs.load(word, lineno);
                } break;
                case NEW_SET: {
                    arg = sets.store(word, lineno);
                } break;
                case SET: {
                    arg = sets.load(word, lineno);
                } break;

                default: {
                    auto i = m_constants.find(std::make_pair(arg_type, word));
                    POMAGMA_ASSERT(
                        i != m_constants.end(),
                        "line " << lineno << ": unknown constant: " << word);
                    arg = i->second;
                } break;
            }
            program.push_back(arg);

            obs.pop(lineno);
            sets.pop(lineno);
        }

        if (op_code == SEQUENCE) {
            uint8_t jump = program.back();
            obs.push(jump, lineno);
            sets.push(jump, lineno);
        }

        POMAGMA_ASSERT(not(stream >> word),
                       "line " << lineno << ": too many arguments: " << word);
    }

    if (not program.empty()) {
        add_program(start_lineno);
    }

    return result;
}

//----------------------------------------------------------------------------
// FileIndex implementation

void FileIndex::add_file(const std::string &filename,
                         const std::vector<Listing> &listings) {
    auto it = std::find(m_filenames.begin(), m_filenames.end(), filename);
    POMAGMA_ASSERT(it == m_filenames.end(), "duplicate filename: " << filename);
    POMAGMA_ASSERT(m_filenames.size() < 255,
                   "Too many source files, limit is 255");
    m_filenames.push_back(filename);

    Hasher hasher;
    hasher.add_file(filename);
    hasher.finish();
    m_hexdigests.push_back(hasher.str());

    // Update sizes and offsets
    size_t size = 0;
    for (const auto &listing : listings) {
        size += listing.size;
    }
    m_sizes.push_back(size);
    size_t previous_offset = m_offsets.empty() ? 0 : m_offsets.back();
    m_offsets.push_back(previous_offset + size);
}

void FileIndex::save_stats(const std::vector<uint32_t> &histogram) const {
    // Create a dense index mapping offset -> filename index
    std::vector<uint8_t> offset_to_filename(histogram.size());
    for (uint8_t i = 0; i < m_filenames.size(); ++i) {
        auto begin = offset_to_filename.begin() + m_offsets[i];
        auto end = i == m_filenames.size() - 1
                       ? offset_to_filename.end()
                       : offset_to_filename.begin() + m_offsets[i + 1];
        std::fill(begin, end, i);
    }

    // Group as filename_idx -> local_offset -> count
    std::map<uint8_t, std::map<uint32_t, uint64_t>> file_counts;
    for (uint32_t offset = 0; offset < histogram.size(); ++offset) {
        uint32_t count = histogram[offset];
        if (!count) continue;
        uint8_t filename_idx = offset_to_filename.at(offset);
        uint32_t local_offset = offset - m_offsets[filename_idx];
        file_counts[filename_idx][local_offset] += count;
    }

    // Write stats file for each file
    for (const auto &[filename_idx, counts] : file_counts) {
        std::string dirname = std::filesystem::path(m_filenames[filename_idx])
                                  .parent_path()
                                  .string();
        const std::string &hexdigest = m_hexdigests[filename_idx];
        std::string filepath = dirname + "/" + hexdigest + ".lineprof";
        write_stats_file(filepath, counts);
    }
}

void FileIndex::write_stats_file(
    const std::string &filepath,
    const std::map<uint32_t, uint64_t> &line_counts) const {
    std::string temp_path = filepath + "." + std::to_string(getpid()) + ".tmp";
    if (std::filesystem::exists(filepath)) {
        // Copy existing counts
        std::filesystem::copy(filepath, temp_path);
    }
    {
        // Append new counts, in append or create mode
        std::ofstream file(temp_path, std::ios::app | std::ios::out);
        POMAGMA_ASSERT(file.is_open(), "Failed to open " << temp_path);
        for (const auto &[lineno, count] : line_counts) {
            file << lineno << "\t" << count << "\n";
        }
        POMAGMA_ASSERT(file.good(), "Failed to write " << temp_path);
    }

    // Atomic rename
    int error = std::rename(temp_path.c_str(), filepath.c_str());
    POMAGMA_ASSERT(error == 0,
                   "Failed to rename " << temp_path << " to " << filepath);
    POMAGMA_INFO("Saved line profile stats to " << filepath);
}

}  // namespace vm
}  // namespace pomagma
