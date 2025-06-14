include_directories(${CMAKE_SOURCE_DIR})

# Google test assumes undefined macros default to 0.
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=undef -Wno-undef")

# We use vcpkg-managed GTest instead of FetchContent
# All test targets should link to GTest::gtest and GTest::gmock

add_subdirectory(farmhash)
