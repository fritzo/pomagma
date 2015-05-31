#include "blobstore.hpp"
#include <atomic>
#include <sys/types.h>
#include <sys/stat.h>

namespace pomagma
{

const char * BLOB_DIR = getenv("POMAGMA_BLOB_DIR");

inline bool path_exists (const std::string& path)
{
    //return std::ifstream(path).good();
    struct stat info;
    return stat(path.c_str(), &info) == 0;
}

std::string find_blob (const std::string & hexdigest)
{
    POMAGMA_ASSERT(BLOB_DIR, "POMAGMA_BLOB_DIR is not defined");
    return rstrip(BLOB_DIR, "/") + "/" + hexdigest;
}

std::string create_blob ()
{
    POMAGMA_ASSERT(BLOB_DIR, "POMAGMA_BLOB_DIR is not defined");
    POMAGMA_ASSERT(path_exists(BLOB_DIR), "POMAGMA_BLOB_DIR does not exist");
    static std::atomic<uint_fast64_t> counter;
    size_t count = counter++;
    std::ostringstream stream;
    stream << rstrip(BLOB_DIR, "/") << "/temp." << getpid() << "." << count;
    std::string path = stream.str();
    if (path_exists(path)) {
        std::remove(path.c_str());
    }
    return stream.str();
}

std::string store_blob (const std::string & temp_path)
{
    const std::string hexdigest = hash_file(temp_path);
    const std::string path = find_blob(hexdigest);

    if (path_exists(path)) {
        std::remove(temp_path.c_str());
    } else {
        std::rename(temp_path.c_str(), path.c_str());
        int info = chmod(path.c_str(), S_IRUSR | S_IRGRP | S_IROTH);
        POMAGMA_ASSERT(info == 0,
            "chmod(" << path << " , readonly) failed with code " << info);
    }

    return hexdigest;
}

} // namespace pomagma
