#include "blobstore.hpp"

#include <fcntl.h>
#include <sys/time.h>

#include <atomic>
#include <cstring>

#define POMAGMA_ASSERT_C(info, message) \
    POMAGMA_ASSERT((info) != -1, message << "; " << strerror(errno))

namespace pomagma {

static const size_t HEXDIGEST_SIZE = 40;

const char* BLOB_DIR = getenv("POMAGMA_BLOB_DIR");

std::string find_blob(const std::string& hexdigest) {
    POMAGMA_ASSERT(BLOB_DIR, "POMAGMA_BLOB_DIR is not defined");
    fs::path path(BLOB_DIR);
    path /= hexdigest;
    return path.string();
}

std::string create_blob() {
    POMAGMA_ASSERT(BLOB_DIR, "POMAGMA_BLOB_DIR is not defined");
    fs::create_directories(BLOB_DIR);
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

inline void touch(const fs::path& path) {
    timeval now;
    gettimeofday(&now, nullptr);
    timeval times[2] = {now, now};
    int info = utimes(path.c_str(), times);
    POMAGMA_ASSERT_C(info, "touch(" << path << ") failed");
}

std::string store_blob(const std::string& temp_path) {
    const std::string hexdigest = hash_file(temp_path);
    POMAGMA_DEBUG("storing blob " << hexdigest);
    store_blob(temp_path, hexdigest);
    return hexdigest;
}

void store_blob(const std::string& temp_path, const std::string& hexdigest) {
    const fs::path path = find_blob(hexdigest);

    if (POMAGMA_DEBUG_LEVEL) {
        const std::string expected = hash_file(temp_path);
        POMAGMA_ASSERT_EQ(hexdigest, expected);
    }

    if (fs::exists(path)) {
        fs::remove(temp_path);
        touch(path);
    } else {
        fs::rename(temp_path, path);
    }
}

std::string load_blob_ref(const std::string& filename) {
    std::ifstream file(filename.c_str(), std::ios::binary);
    POMAGMA_ASSERT(file, "failed to open blob ref " << filename);
    std::string hexdigest;
    hexdigest.resize(HEXDIGEST_SIZE);
    file.read(&hexdigest[0], hexdigest.size());
    POMAGMA_ASSERT(file, "failed to load blob ref from " << filename);
    return hexdigest;
}

void dump_blob_ref(const std::string& hexdigest, const std::string& filename,
                   const std::vector<std::string>& sub_hexdigests) {
    POMAGMA_ASSERT_EQ(hexdigest.size(), HEXDIGEST_SIZE);
    int fid = creat(filename.c_str(), 0444);
    POMAGMA_ASSERT(fid != -1,
                   "creating " << filename << ": " << strerror(errno));
    POMAGMA_ASSERT(write(fid, hexdigest.data(), hexdigest.size()) != -1,
                   "writing " << filename << ": " << strerror(errno));
    for (const auto& sub_hexdigest : sub_hexdigests) {
        POMAGMA_ASSERT_EQ(sub_hexdigest.size(), HEXDIGEST_SIZE);
        POMAGMA_ASSERT(write(fid, "\n", 1) != -1,
                       "writing " << filename << ": " << strerror(errno));
        POMAGMA_ASSERT(write(fid, sub_hexdigest.data(), HEXDIGEST_SIZE) != -1,
                       "writing " << filename << ": " << strerror(errno));
    }
    POMAGMA_ASSERT(close(fid) != -1,
                   "closing " << filename << ": " << strerror(errno));
}

}  // namespace pomagma
