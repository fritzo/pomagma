#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/util/hasher.hpp>

namespace pomagma {

extern const char * BLOB_DIR;

inline std::string hash_file (const std::string & filename)
{
    Hasher hasher;
    hasher.add_file(filename);
    hasher.finish();
    return hasher.str();
}

// return path to read-only file
std::string find_blob (const std::string & hexdigest);

// return temp_path to write blob to
std::string create_blob ();

// return digest for future find_blob calls; removes temp file
std::string store_blob (const std::string & temp_path)
    __attribute__((warn_unused_result));

// assume digest has already been computed; removes temp file
void store_blob (const std::string & temp_path, const std::string & hexdigest);

// return hexdigest read from file
std::string load_blob_ref (const std::string & filename);

// write hexdigest to file
void dump_blob_ref (
        const std::string & hexdigest,
        const std::string & filename);

} // namespace pomagma
