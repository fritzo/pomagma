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

template<class Ob, class SetPtr>
struct Context_
{
    Ob obs[256];
    const SetPtr * sets[256];
    size_t block;
    size_t trace;
    ProgramProfiler profiler;

    void clear ()
    {
        std::fill(std::begin(obs), std::end(obs), 0);
        std::fill(std::begin(sets), std::end(sets), nullptr);
        block = 0;
        trace = 0;
    }
} __attribute__((aligned(64)));

typedef const uint8_t * Program;
struct Listing
{
    size_t program_offset;
    size_t size;
    size_t lineno;
};

class ProgramParser
{
public:

    void load (Signature & signature); // TODO input a proto, not Signature

    std::vector<Listing> parse (std::istream & infile);
    std::vector<Listing> parse_file (const std::string & filename);

    // WARNING Calling parse() or parse_file() invalidates the returned Program.
    Program find_program (const Listing & listing) const
    {
        POMAGMA_ASSERT_LE(
            listing.program_offset + listing.size,
            m_program_data.size());
        return m_program_data.data() + listing.program_offset;
    }

private:

    std::vector<uint8_t> m_program_data; // all programs in contiguous memory
    std::map<std::pair<OpArgType, std::string>, uint8_t> m_constants;

    class SymbolTable;
    class SymbolTableStack;
};

/*
template<class Ob, class SetPtr>
void dump_continuation (Program, const Context * context, std::string & message)
{
    message.clear();

}

template<class Ob, class SetPtr>
Program load_continuation (Context * context, const std::string & message)
{
}
*/

} // namespace vm
} // namespacepomagma
