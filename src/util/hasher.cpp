#include "hasher.hpp"
#include <cstdio>

namespace pomagma {

void Hasher::add_file(const std::string &filename) {
    unsigned char buffer[8192];
    FILE *file = fopen(filename.c_str(), "rb");
    POMAGMA_ASSERT(file, "failed to open file " << filename);

    while (size_t size = fread(buffer, 1, sizeof buffer, file)) {
        add_raw(buffer, size);
    }

    int error = ferror(file);
    fclose(file);
    POMAGMA_ASSERT(not error, "failed reading file " << filename);
}

std::string print_digest(const Hasher::Digest &digest) {
    static constexpr char print[] = "0123456789abcdef";

    std::string hex;
    hex.reserve(digest.size() * 2);
    for (uint8_t i : digest) {
        hex.push_back(print[i / 16]);
        hex.push_back(print[i % 16]);
    }

    return hex;
}

Hasher::Digest parse_digest(const std::string &hex) {
    static constexpr uint8_t parse[256] = {
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,  0,  0,
        0,  0,  0,  0,                                          // 0-9
        0,  10, 11, 12, 13, 14, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0,  // A-F
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 11, 12,
        13, 14, 15, 0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0, 0, 0, 0};

    POMAGMA_ASSERT_EQ(hex.size(), 2 * SHA_DIGEST_LENGTH);
    Hasher::Digest digest(SHA_DIGEST_LENGTH);
    const uint8_t *hex_data = reinterpret_cast<const uint8_t *>(hex.data());
    for (size_t i = 0; i < SHA_DIGEST_LENGTH; ++i) {
        digest[i] = parse[hex_data[2 * i]] * 16 + parse[hex_data[2 * i + 1]];
    }

    return digest;
}

}  // namespace pomagma
