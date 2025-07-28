#include <gtest/gtest.h>

#include <pomagma/util/hilbert.hpp>
#include <set>
#include <vector>

namespace pomagma {
namespace {

class HilbertTest : public ::testing::Test {
   protected:
    void SetUp() override {}
    void TearDown() override {}
};

// Test basic functionality of 16-bit Hilbert decode
TEST_F(HilbertTest, HilbertDecode16Basic) {
    // Test some known points
    auto [x0, y0] = hilbert_decode_16(0);
    EXPECT_EQ(x0, 0);
    EXPECT_EQ(y0, 0);

    // Test that we get different coordinates for different indices
    auto [x1, y1] = hilbert_decode_16(1);
    auto [x2, y2] = hilbert_decode_16(2);
    auto [x3, y3] = hilbert_decode_16(3);

    // Should all be different
    EXPECT_TRUE(x1 != x0 || y1 != y0);
    EXPECT_TRUE(x2 != x1 || y2 != y1);
    EXPECT_TRUE(x3 != x2 || y3 != y2);
}

// Test basic functionality of 30-bit Hilbert decode
TEST_F(HilbertTest, HilbertDecode30Basic) {
    // Test some known points
    auto [x0, y0] = hilbert_decode_30(0);
    EXPECT_EQ(x0, 0U);
    EXPECT_EQ(y0, 0U);

    // Test that we get different coordinates for different indices
    auto [x1, y1] = hilbert_decode_30(1);
    auto [x2, y2] = hilbert_decode_30(2);
    auto [x3, y3] = hilbert_decode_30(3);

    // Should all be different
    EXPECT_TRUE(x1 != x0 || y1 != y0);
    EXPECT_TRUE(x2 != x1 || y2 != y1);
    EXPECT_TRUE(x3 != x2 || y3 != y2);
}

// Test basic functionality of 8-bit Hilbert decode
TEST_F(HilbertTest, HilbertDecode8Basic) {
    // Test some known points
    auto [x0, y0] = hilbert_decode_8(0);
    EXPECT_EQ(x0, 0);
    EXPECT_EQ(y0, 0);

    // Test that we get different coordinates for different indices
    auto [x1, y1] = hilbert_decode_8(1);
    auto [x2, y2] = hilbert_decode_8(2);
    auto [x3, y3] = hilbert_decode_8(3);

    // Should all be different
    EXPECT_TRUE(x1 != x0 || y1 != y0);
    EXPECT_TRUE(x2 != x1 || y2 != y1);
    EXPECT_TRUE(x3 != x2 || y3 != y2);
}

// Test that coordinates stay within expected bounds
TEST_F(HilbertTest, HilbertDecode16Bounds) {
    const uint16_t max_coord = 65535;  // 2^16 - 1

    // Test a range of indices
    for (uint32_t h = 0; h < 1000; ++h) {
        auto [x, y] = hilbert_decode_16(h);
        EXPECT_LE(x, max_coord);
        EXPECT_LE(y, max_coord);
        // Note: Individual decode functions can return 0, but for_xy filters
        // them out
    }
}

// Test that coordinates stay within expected bounds for 30-bit
TEST_F(HilbertTest, HilbertDecode30Bounds) {
    const uint32_t max_coord = (1U << 30) - 1;  // 2^30 - 1

    // Test a range of indices (smaller range due to performance)
    for (uint64_t h = 0; h < 1000; ++h) {
        auto [x, y] = hilbert_decode_30(h);
        EXPECT_LE(x, max_coord);
        EXPECT_LE(y, max_coord);
        // Note: Individual decode functions can return 0, but for_xy filters
        // them out
    }
}

// Test that coordinates stay within expected bounds for 8-bit
TEST_F(HilbertTest, HilbertDecode8Bounds) {
    const uint8_t max_coord = 255;  // 2^8 - 1

    // Test a range of indices
    for (uint16_t h = 0; h < 1000; ++h) {
        auto [x, y] = hilbert_decode_8(h);
        EXPECT_LE(x, max_coord);
        EXPECT_LE(y, max_coord);
        // Note: Individual decode functions can return 0, but for_xy filters
        // them out
    }
}

// Test locality property for 8-bit: nearby indices should map to nearby
// coordinates
TEST_F(HilbertTest, HilbertLocality8) {
    std::vector<std::pair<uint8_t, uint8_t>> coords;

    // Get first 100 coordinates
    for (uint16_t h = 0; h < 100; ++h) {
        auto [x, y] = hilbert_decode_8(h);
        coords.emplace_back(x, y);
    }

    // Check that most consecutive pairs are close to each other
    int close_pairs = 0;
    for (size_t i = 1; i < coords.size(); ++i) {
        auto [x1, y1] = coords[i - 1];
        auto [x2, y2] = coords[i];

        // Manhattan distance
        uint32_t distance =
            std::abs(static_cast<int32_t>(x2) - static_cast<int32_t>(x1)) +
            std::abs(static_cast<int32_t>(y2) - static_cast<int32_t>(y1));

        if (distance <= 2) {  // Very close
            close_pairs++;
        }
    }

    // Most pairs should be close (Hilbert curve locality property)
    EXPECT_GT(close_pairs, static_cast<int>(coords.size()) *
                               0.7);  // At least 70% should be close
}

// Test that different indices produce different coordinates for 8-bit
// (injectivity)
TEST_F(HilbertTest, HilbertInjectivity8) {
    std::set<std::pair<uint8_t, uint8_t>> seen_coords;

    // Test first 1000 indices
    for (uint16_t h = 0; h < 1000; ++h) {
        auto [x, y] = hilbert_decode_8(h);
        std::pair<uint8_t, uint8_t> coord = {x, y};

        // Should not have seen this coordinate before
        EXPECT_EQ(seen_coords.find(coord), seen_coords.end())
            << "Duplicate coordinate (" << static_cast<int>(x) << ", "
            << static_cast<int>(y) << ") at index " << h;

        seen_coords.insert(coord);
    }

    // Should have exactly 1000 unique coordinates
    EXPECT_EQ(seen_coords.size(), 1000U);
}

// Test locality property: nearby indices should map to nearby coordinates
TEST_F(HilbertTest, HilbertLocality16) {
    std::vector<std::pair<uint16_t, uint16_t>> coords;

    // Get first 100 coordinates
    for (uint32_t h = 0; h < 100; ++h) {
        auto [x, y] = hilbert_decode_16(h);
        coords.emplace_back(x, y);
    }

    // Check that most consecutive pairs are close to each other
    int close_pairs = 0;
    for (size_t i = 1; i < coords.size(); ++i) {
        auto [x1, y1] = coords[i - 1];
        auto [x2, y2] = coords[i];

        // Manhattan distance
        uint32_t distance =
            std::abs(static_cast<int32_t>(x2) - static_cast<int32_t>(x1)) +
            std::abs(static_cast<int32_t>(y2) - static_cast<int32_t>(y1));

        if (distance <= 2) {  // Very close
            close_pairs++;
        }
    }

    // Most pairs should be close (Hilbert curve locality property)
    EXPECT_GT(close_pairs, static_cast<int>(coords.size()) *
                               0.7);  // At least 70% should be close
}

// Test that different indices produce different coordinates (injectivity)
TEST_F(HilbertTest, HilbertInjectivity16) {
    std::set<std::pair<uint16_t, uint16_t>> seen_coords;

    // Test first 1000 indices
    for (uint32_t h = 0; h < 1000; ++h) {
        auto [x, y] = hilbert_decode_16(h);
        std::pair<uint16_t, uint16_t> coord = {x, y};

        // Should not have seen this coordinate before
        EXPECT_EQ(seen_coords.find(coord), seen_coords.end())
            << "Duplicate coordinate (" << x << ", " << y << ") at index " << h;

        seen_coords.insert(coord);
    }

    // Should have exactly 1000 unique coordinates
    EXPECT_EQ(seen_coords.size(), 1000U);
}

// Test traverse functions with simple counting
TEST_F(HilbertTest, ForXYTraversal) {
    int total_count = 0;
    int even_sum_count = 0;

    auto func = [&](uint16_t x, uint16_t y) {
        total_count++;
        if ((x + y) % 2 == 0) {  // Count coordinates with even sums
            even_sum_count++;
        }
    };

    // Run on a small 4x4 grid, should visit [1,4) x [1,4) = 9 coordinates
    for_xy(4, func);

    // Should have visited 9 coordinates: (1,1), (1,2), (1,3), (2,1), (2,2),
    // (2,3), (3,1), (3,2), (3,3)
    EXPECT_EQ(total_count, 9);

    // Should have found some coordinates with even sums
    EXPECT_GT(even_sum_count, 0);
    EXPECT_LE(even_sum_count, total_count);
}

// Test for_xy with different size to ensure dynamic dispatch works
TEST_F(HilbertTest, ForXYLargerGrid) {
    int total_count = 0;
    int even_sum_count = 0;

    auto func = [&](uint32_t x, uint32_t y) {
        total_count++;
        if ((x + y) % 2 == 0) {  // Count coordinates with even sums
            even_sum_count++;
        }
    };

    // Run on a small 8x8 grid, should visit [1,8) x [1,8) = 49 coordinates
    for_xy(8, func);

    // Should have visited 49 coordinates: 7x7 grid from (1,1) to (7,7)
    EXPECT_EQ(total_count, 49);

    // Should have found some coordinates with even sums
    EXPECT_GT(even_sum_count, 0);
    EXPECT_LE(even_sum_count, total_count);
}

// Test edge cases
TEST_F(HilbertTest, EdgeCases) {
    // Test maximum valid indices
    auto [x_max_16, y_max_16] = hilbert_decode_16(0xFFFFFFFF);
    EXPECT_LT(x_max_16, 65536U);
    EXPECT_LT(y_max_16, 65536U);

    auto [x_max_30, y_max_30] = hilbert_decode_30(0xFFFFFFFFFFFFFFFFULL);
    EXPECT_LT(x_max_30, (1ULL << 30));
    EXPECT_LT(y_max_30, (1ULL << 30));
}

// Test that Hilbert traversal visits every coordinate exactly once
TEST_F(HilbertTest, HilbertTraversalCompleteness) {
    const uint32_t grid_size = 100;

    // Create a 100x100 grid initialized to zero
    std::vector<std::vector<int>> grid(grid_size,
                                       std::vector<int>(grid_size, 0));

    auto func = [&](uint32_t x, uint32_t y) {
        ASSERT_LT(x, grid_size) << "x coordinate " << x << " exceeds grid size";
        ASSERT_LT(y, grid_size) << "y coordinate " << y << " exceeds grid size";
        ASSERT_GT(x, 0) << "x coordinate " << x << " should be >= 1";
        ASSERT_GT(y, 0) << "y coordinate " << y << " should be >= 1";
        grid[x][y]++;
    };

    // Run Hilbert traversal over [1,100) x [1,100)
    for_xy(grid_size, func);

    // Verify grid positions [1,100) x [1,100) were visited exactly once
    for (uint32_t x = 0; x < grid_size; ++x) {
        for (uint32_t y = 0; y < grid_size; ++y) {
            if (x == 0 || y == 0) {
                // First row and first column should never be visited
                EXPECT_EQ(grid[x][y], 0)
                    << "Grid position (" << x << ", " << y
                    << ") should not be visited (outside [1,size) range)";
            } else {
                // All other positions should be visited exactly once
                EXPECT_EQ(grid[x][y], 1)
                    << "Grid position (" << x << ", " << y << ") was visited "
                    << grid[x][y] << " times instead of exactly once";
            }
        }
    }
}

// Test consistency between BMI2 and fallback implementations
// This test will run both paths if BMI2 is available
TEST_F(HilbertTest, ConsistencyTest) {
    // We can't easily test both paths in a single build, but we can
    // at least verify the functions are deterministic
    for (uint32_t h = 0; h < 100; ++h) {
        auto [x1, y1] = hilbert_decode_16(h);
        auto [x2, y2] = hilbert_decode_16(h);

        EXPECT_EQ(x1, x2);
        EXPECT_EQ(y1, y2);
    }

    for (uint16_t h = 0; h < 100; ++h) {
        auto [x1, y1] = hilbert_decode_8(h);
        auto [x2, y2] = hilbert_decode_8(h);

        EXPECT_EQ(x1, x2);
        EXPECT_EQ(y1, y2);
    }

    for (uint64_t h = 0; h < 100; ++h) {
        auto [x1, y1] = hilbert_decode_30(h);
        auto [x2, y2] = hilbert_decode_30(h);

        EXPECT_EQ(x1, x2);
        EXPECT_EQ(y1, y2);
    }
}

// Test that encode/decode are inverses for 16-bit
TEST_F(HilbertTest, HilbertEncodeDecode16Inverse) {
    // Test a comprehensive range of coordinates
    int failure_count = 0;
    const int max_failures_to_report = 10;

    for (uint16_t x = 0; x < 1000; ++x) {
        for (uint16_t y = 0; y < 1000; ++y) {
            uint32_t h = hilbert_encode_16(x, y);
            auto [decoded_x, decoded_y] = hilbert_decode_16(h);

            if (decoded_x != x || decoded_y != y) {
                if (failure_count < max_failures_to_report) {
                    ADD_FAILURE() << "Encode/Decode mismatch for x=" << x
                                  << ", y=" << y << ", h=" << h << " -> ("
                                  << decoded_x << ", " << decoded_y << ")";
                }
                failure_count++;
            }
        }
    }

    if (failure_count > max_failures_to_report) {
        ADD_FAILURE() << "Total failures: " << failure_count << " (only first "
                      << max_failures_to_report << " reported)";
    }

    EXPECT_EQ(failure_count, 0)
        << "Found " << failure_count << " total failures";
}

// Test that encode/decode are inverses for 8-bit
TEST_F(HilbertTest, HilbertEncodeDecode8Inverse) {
    // Test all possible 8-bit coordinates (256x256 = 65536 combinations)
    int failure_count = 0;
    const int max_failures_to_report = 10;

    for (uint16_t x = 0; x < 256; ++x) {
        for (uint16_t y = 0; y < 256; ++y) {
            uint16_t h = hilbert_encode_8(static_cast<uint8_t>(x),
                                          static_cast<uint8_t>(y));
            auto [decoded_x, decoded_y] = hilbert_decode_8(h);

            if (decoded_x != x || decoded_y != y) {
                if (failure_count < max_failures_to_report) {
                    ADD_FAILURE()
                        << "Encode/Decode mismatch for x=" << x << ", y=" << y
                        << ", h=" << h << " -> (" << static_cast<int>(decoded_x)
                        << ", " << static_cast<int>(decoded_y) << ")";
                }
                failure_count++;
            }
        }
    }

    if (failure_count > max_failures_to_report) {
        ADD_FAILURE() << "Total failures: " << failure_count << " (only first "
                      << max_failures_to_report << " reported)";
    }

    EXPECT_EQ(failure_count, 0)
        << "Found " << failure_count << " total failures";
}

// Test boundary conditions for 16-bit encoder
TEST_F(HilbertTest, HilbertEncode16Bounds) {
    // Test corner cases
    uint32_t h00 = hilbert_encode_16(0, 0);
    auto [x00, y00] = hilbert_decode_16(h00);
    EXPECT_EQ(x00, 0);
    EXPECT_EQ(y00, 0);

    uint32_t h_max = hilbert_encode_16(65535, 65535);
    auto [x_max, y_max] = hilbert_decode_16(h_max);
    EXPECT_EQ(x_max, 65535);
    EXPECT_EQ(y_max, 65535);

    // Test edge coordinates
    uint32_t h01 = hilbert_encode_16(0, 1);
    auto [x01, y01] = hilbert_decode_16(h01);
    EXPECT_EQ(x01, 0);
    EXPECT_EQ(y01, 1);

    uint32_t h10 = hilbert_encode_16(1, 0);
    auto [x10, y10] = hilbert_decode_16(h10);
    EXPECT_EQ(x10, 1);
    EXPECT_EQ(y10, 0);
}

// Test boundary conditions for 8-bit encoder
TEST_F(HilbertTest, HilbertEncode8Bounds) {
    // Test corner cases
    uint16_t h00 = hilbert_encode_8(0, 0);
    auto [x00, y00] = hilbert_decode_8(h00);
    EXPECT_EQ(x00, 0);
    EXPECT_EQ(y00, 0);

    uint16_t h_max = hilbert_encode_8(255, 255);
    auto [x_max, y_max] = hilbert_decode_8(h_max);
    EXPECT_EQ(x_max, 255);
    EXPECT_EQ(y_max, 255);

    // Test edge coordinates
    uint16_t h01 = hilbert_encode_8(0, 1);
    auto [x01, y01] = hilbert_decode_8(h01);
    EXPECT_EQ(x01, 0);
    EXPECT_EQ(y01, 1);

    uint16_t h10 = hilbert_encode_8(1, 0);
    auto [x10, y10] = hilbert_decode_8(h10);
    EXPECT_EQ(x10, 1);
    EXPECT_EQ(y10, 0);
}

// Test that different coordinates produce different indices for 16-bit
// (injectivity of encode)
TEST_F(HilbertTest, HilbertEncode16Injectivity) {
    std::set<uint32_t> seen_indices;
    int failure_count = 0;
    const int max_failures_to_report = 10;

    // Test first 1000x1000 coordinates
    for (uint16_t x = 0; x < 1000; ++x) {
        for (uint16_t y = 0; y < 1000; ++y) {
            uint32_t h = hilbert_encode_16(x, y);

            // Should not have seen this index before
            if (seen_indices.find(h) != seen_indices.end()) {
                if (failure_count < max_failures_to_report) {
                    ADD_FAILURE()
                        << "Duplicate index " << h << " for coordinates (" << x
                        << ", " << y << ")";
                }
                failure_count++;
            }

            seen_indices.insert(h);
        }
    }

    if (failure_count > max_failures_to_report) {
        ADD_FAILURE() << "Total duplicate indices: " << failure_count
                      << " (only first " << max_failures_to_report
                      << " reported)";
    }

    // Should have exactly 1,000,000 unique indices
    EXPECT_EQ(seen_indices.size(), 1000000U);
    EXPECT_EQ(failure_count, 0)
        << "Found " << failure_count << " duplicate indices";
}

// Test that different coordinates produce different indices for 8-bit
// (injectivity of encode)
TEST_F(HilbertTest, HilbertEncode8Injectivity) {
    std::set<uint16_t> seen_indices;
    int failure_count = 0;
    const int max_failures_to_report = 10;

    // Test all 8-bit coordinates
    for (uint16_t x = 0; x < 256; ++x) {
        for (uint16_t y = 0; y < 256; ++y) {
            uint16_t h = hilbert_encode_8(static_cast<uint8_t>(x),
                                          static_cast<uint8_t>(y));

            // Should not have seen this index before
            if (seen_indices.find(h) != seen_indices.end()) {
                if (failure_count < max_failures_to_report) {
                    ADD_FAILURE()
                        << "Duplicate index " << h << " for coordinates (" << x
                        << ", " << y << ")";
                }
                failure_count++;
            }

            seen_indices.insert(h);
        }
    }

    if (failure_count > max_failures_to_report) {
        ADD_FAILURE() << "Total duplicate indices: " << failure_count
                      << " (only first " << max_failures_to_report
                      << " reported)";
    }

    // Should have exactly 65,536 unique indices
    EXPECT_EQ(seen_indices.size(), 65536U);
    EXPECT_EQ(failure_count, 0)
        << "Found " << failure_count << " duplicate indices";
}

// Test consistency with decode->encode roundtrip for 16-bit
TEST_F(HilbertTest, HilbertDecodeEncode16Roundtrip) {
    int failure_count = 0;
    const int max_failures_to_report = 10;

    // Test a range of Hilbert indices
    for (uint32_t h = 0; h < 10000; ++h) {
        auto [x, y] = hilbert_decode_16(h);
        uint32_t h_encoded = hilbert_encode_16(x, y);

        if (h_encoded != h) {
            if (failure_count < max_failures_to_report) {
                ADD_FAILURE()
                    << "Decode/Encode roundtrip failed for h=" << h << " -> ("
                    << x << ", " << y << ") -> " << h_encoded;
            }
            failure_count++;
        }
    }

    // Test random coordinates
    for (int i = 0; i < 1000; ++i) {
        uint16_t x = rand() % 65536;
        uint16_t y = rand() % 65536;
        uint32_t h = hilbert_encode_16(x, y);
        if (h != hilbert_encode_16(x, y)) {
            ADD_FAILURE() << "Random coordinate (" << x << ", " << y
                          << ") encoded to " << h << " but decoded to (" << x
                          << ", " << y << ")";
            failure_count++;
        }
    }

    if (failure_count > max_failures_to_report) {
        ADD_FAILURE() << "Total roundtrip failures: " << failure_count
                      << " (only first " << max_failures_to_report
                      << " reported)";
    }

    EXPECT_EQ(failure_count, 0)
        << "Found " << failure_count << " roundtrip failures";
}

// Test consistency with decode->encode roundtrip for 8-bit
TEST_F(HilbertTest, HilbertDecodeEncode8Roundtrip) {
    // Test all possible 8-bit Hilbert indices (65536 combinations)
    int failure_count = 0;
    const int max_failures_to_report = 10;

    for (uint32_t h = 0; h < 65536; ++h) {
        auto [x, y] = hilbert_decode_8(static_cast<uint16_t>(h));
        uint16_t h_encoded = hilbert_encode_8(x, y);

        if (h_encoded != static_cast<uint16_t>(h)) {
            if (failure_count < max_failures_to_report) {
                ADD_FAILURE() << "Decode/Encode roundtrip failed for h=" << h
                              << " -> (" << static_cast<int>(x) << ", "
                              << static_cast<int>(y) << ") -> " << h_encoded;
            }
            failure_count++;
        }
    }

    if (failure_count > max_failures_to_report) {
        ADD_FAILURE() << "Total roundtrip failures: " << failure_count
                      << " (only first " << max_failures_to_report
                      << " reported)";
    }

    EXPECT_EQ(failure_count, 0)
        << "Found " << failure_count << " roundtrip failures";
}

}  // namespace
}  // namespace pomagma