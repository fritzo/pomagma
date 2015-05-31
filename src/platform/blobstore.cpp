#include "blobstore.hpp"
#include <sys/stat.h>  // for chmod

namespace pomagma
{

const char * BLOB_DIR = getenv_default("POMAGMA_BLOB_DIR", "TODO getcwd()");

std::string load_blob (const std::string & hexdigest)
{
    POMAGMA_ASSERT(not endswith(BLOB_DIR, "/"),
        "POMAGMA_BLOB_DIR has trailing /");

    return std::string(BLOB_DIR) + "/" + hexdigest;
}

std::string store_blob (const std::string & temp_path)
{
    const std::string hexdigest = hash_file(temp_path);
    const std::string path = load_blob(hexdigest);

    if (std::ifstream(path).good()) {
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
