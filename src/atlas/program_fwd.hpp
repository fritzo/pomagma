#pragma once

#include <algorithm>
#include <map>
#include <pomagma/util/aligned_alloc.hpp>
#include <pomagma/util/profiler.hpp>
#include <vector>

namespace pomagma {
class Signature;
namespace vm {

typedef std::vector<uint8_t> Listing;
typedef const uint8_t * Program;

enum OpCode : uint8_t;
enum OpArgType : uint8_t;

class ProgramParser
{
public:

    ProgramParser (Signature & signature); // TODO input a proto, not Signature
    std::vector<std::pair<Listing, size_t>> parse (std::istream & infile) const;
    std::vector<std::pair<Listing, size_t>> parse_file (
            const std::string & filename) const;

private:

    std::map<std::pair<OpArgType, std::string>, uint8_t> m_constants;

    class SymbolTable;
    class SymbolTableStack;
};

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

} // namespace vm
} // namespacepomagma
