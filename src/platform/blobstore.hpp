#pragma once

#include <pomagma/platform/util.hpp>
#include <pomagma/platform/hasher.hpp>

namespace pomagma
{

extern const char * BLOB_DIR;

inline std::string hash_file (const std::string & filename)
{
    Hasher hasher;
    hasher.add_file(filename);
    return hasher.str();
}

// returns path to read-only file
std::string find_blob (const std::string & hexdigest);

// returns temp_path to write blob to
std::string create_blob ();

// returns digest to find file later; takes ownership of file
std::string store_blob (const std::string & temp_path);

} // namespace pomagma
