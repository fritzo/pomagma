#include "blobstore.hpp"
#include <atomic>
#include <fcntl.h>

#ifndef O_BINARY
#  define O_BINARY 0
#  define O_TEXT 0
#endif

namespace pomagma
{

const char * BLOB_DIR = getenv("POMAGMA_BLOB_DIR");

std::string find_blob (const std::string & hexdigest)
{
    POMAGMA_ASSERT(BLOB_DIR, "POMAGMA_BLOB_DIR is not defined");
    fs::path path(BLOB_DIR);
    path /= hexdigest;
    return path.string();
}

std::string create_blob ()
{
    POMAGMA_ASSERT(BLOB_DIR, "POMAGMA_BLOB_DIR is not defined");
    POMAGMA_ASSERT(fs::exists(BLOB_DIR), "POMAGMA_BLOB_DIR does not exist");
    static std::atomic<uint_fast64_t> counter;
    size_t pid = getpid();
    size_t count = counter++;
    std::ostringstream stream;
    stream << "temp." << pid << "." << count;
    fs::path path(BLOB_DIR);
    path /= stream.str();
    if (fs::exists(path)) {
        POMAGMA_DEBUG("removing temp file " << path);
        fs::remove(path);
    }
    return path.string();
}

std::string store_blob (const std::string & temp_path)
{
    const std::string hexdigest = hash_file(temp_path);
    const fs::path path = find_blob(hexdigest);

    if (fs::exists(path)) {
        fs::remove(temp_path);
    } else {
        fs::rename(temp_path, path);
    }

    return hexdigest;
}

std::string load_blob_ref (const std::string & filename)
{
    std::ifstream file(filename.c_str(), std::ios::binary);
    POMAGMA_ASSERT(file, "failed to open blob ref " << filename);
    std::string hexdigest;
    hexdigest.resize(40);
    file.read(& hexdigest[0], hexdigest.size());
    POMAGMA_ASSERT(file, "failed to load blob ref from " << filename);
    return hexdigest;
}

void dump_blob_ref (const std::string & hexdigest, const std::string & filename)
{
    POMAGMA_ASSERT_EQ(hexdigest.size(), 40);
    int fd = open(filename.c_str(), O_WRONLY | O_BINARY, 0444);
    POMAGMA_ASSERT(fd != -1, "failed to create blob ref " << filename);
    int info = write(fd, hexdigest.data(), hexdigest.size());
    POMAGMA_ASSERT(info != -1, "failed to dump blob ref " << filename);
    info = close(fd);
    POMAGMA_ASSERT(info != -1, "failed to close blob ref " << filename);
}

} // namespace pomagma
