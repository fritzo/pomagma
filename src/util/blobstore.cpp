#include "blobstore.hpp"

#include <atomic>
#include <fcntl.h>
#include <sys/time.h>

#define POMAGMA_ASSERT_C(info, message) \
    POMAGMA_ASSERT((info) != -1, message << "; " << strerror(errno))

namespace pomagma {

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

inline void touch (const fs::path & path)
{
    timeval now;
    gettimeofday(& now, nullptr);
    timeval times[2] = {now, now};
    int info = utimes(path.c_str(), times);
    POMAGMA_ASSERT_C(info, "touch(" << path << ") failed");
}

std::string store_blob (const std::string & temp_path)
{
    const std::string hexdigest = hash_file(temp_path);
    store_blob(temp_path, hexdigest);
    return hexdigest;
}

void store_blob (const std::string & temp_path, const std::string & hexdigest)
{
    const fs::path path = find_blob(hexdigest);

    if (POMAGMA_DEBUG_LEVEL) {
        const std::string expected = hash_file(hexdigest);
        POMAGMA_ASSERT_EQ(hexdigest, expected);
    }

    if (fs::exists(path)) {
        fs::remove(temp_path);
        touch(path);
    } else {
        fs::rename(temp_path, path);
    }
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
#define USE_PERMISSION_CONSIOUS_DUMP (0)
#if USE_PERMISSION_CONSIOUS_DUMP

    // FIXME why does this permissions-consious version fail?
    POMAGMA_ASSERT_EQ(hexdigest.size(), 40);
    int fd = open(filename.c_str(), O_WRONLY, 0444);
    POMAGMA_ASSERT(fd, "failed to create blob ref " << filename);
    int info = write(fd, hexdigest.data(), hexdigest.size());
    POMAGMA_ASSERT(info, "failed to dump blob ref to " << filename);
    info = close(fd);
    POMAGMA_ASSERT(info, "failed to close blob ref " << filename);

#else // USE_PERMISSION_CONSIOUS_DUMP

    std::ofstream file(filename.c_str(), std::ios::binary);
    POMAGMA_ASSERT(file, "failed to create blob ref " << filename);
    file.write(hexdigest.data(), hexdigest.size());
    POMAGMA_ASSERT(file, "failed to dump blob ref to " << filename);

#endif // USE_PERMISSION_CONSIOUS_DUMP
}

} // namespace pomagma
