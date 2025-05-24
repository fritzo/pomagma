include_directories(${CMAKE_SOURCE_DIR}/include)

# Google test assumes undefined macros default to 0.
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=undef -Wno-undef")

# Use FetchContent for GoogleTest instead of vendored copies
include(FetchContent)

# Fetch GoogleTest 
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        v1.15.2  # Latest stable release
)

# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

# Make googletest available
FetchContent_MakeAvailable(googletest)

add_subdirectory(farmhash)
