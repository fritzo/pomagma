cmake_minimum_required(VERSION 3.10)

# Set up vcpkg toolchain before project() call
if(DEFINED ENV{VCPKG_ROOT})
  set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
      CACHE STRING "Vcpkg toolchain file")
elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/vcpkg/scripts/buildsystems/vcpkg.cmake")
  set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_SOURCE_DIR}/vcpkg/scripts/buildsystems/vcpkg.cmake"
      CACHE STRING "Vcpkg toolchain file")
endif()

project(pomagma)
set(CMAKE_MACOSX_RPATH 1)

# Export compile commands for language servers (clangd, etc.)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(DEFINED ENV{CC})
  set(CMAKE_C_COMPILER "$ENV{CC}")
endif()
if(DEFINED ENV{CXX})
  set(CMAKE_CXX_COMPILER "$ENV{CXX}")
endif()

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Woverloaded-virtual -Wsign-promo -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wno-deprecated")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -fomit-frame-pointer -pipe")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ftree-vectorize")
if(DEFINED ENV{CI})
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mtune=native")
else()
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=native")
endif()
if(DEFINED ENV{POMAGMA_NO_OPENMP})
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=unknown-pragmas")
else()
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp")
endif()
# This is very verbose:
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize")

# Architecture-specific flags
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DPOMAGMA_ASSUME_X86")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64)$")
  # ARM64-specific flags (if any needed in future)
  message(STATUS "Building for ARM64 architecture")
endif()

set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS} -DPOMAGMA_DEBUG_LEVEL=9")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "${CMAKE_CXX_FLAGS} -DNDEBUG=1")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASHSELFTEST=0")
if(DEFINED ENV{CI})
else()
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_SSSE3")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_SSE41")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_SSE42")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_AESNI")
  endif()
endif()
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_CAN_USE_CXX11")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS} -DFARMHASH_DEBUG=0")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "${CMAKE_CXX_FLAGS} -DFARMHASH_DEBUG=1")

# tcmalloc appears to leak, so we avoid it
#SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free")

if(APPLE)
  # TODO Decide which shared linker options:
  set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-undefined,dynamic_lookup")
  # set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-undefined,warning,-flat_namespace")
endif()

message(STATUS "CMake using ${CMAKE_CXX_COMPILER_ID} C++ compiler")
if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -funswitch-loops")
  if(APPLE)
    # see http://stackoverflow.com/questions/10327939
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mno-avx")
    #set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wa,-q")
  endif()
elseif("${CMAKE_CXX_COMPILER_ID}" MATCHES "Clang")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=mismatched-tags")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Qunused-arguments")
  #set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ferror-limit 1")
  
  # Use libc++ on macOS, libstdc++ on Linux for better compatibility
  if(APPLE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
  endif()
  
  # Workaround for LLVM 18+ with Abseil compatibility issue
  # See: https://github.com/abseil/abseil-cpp/issues/1747
  # Commented out to match vcpkg ABI
  # set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fclang-abi-compat=17")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Intel")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC")
endif()
message(STATUS "CMake C++ flags: ${CMAKE_CXX_FLAGS}")

# Use vcpkg-managed dependencies
find_package(protobuf REQUIRED)
find_package(absl CONFIG REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(TBB CONFIG REQUIRED)
find_package(PkgConfig REQUIRED)
find_package(GTest CONFIG REQUIRED)
find_package(ZLIB REQUIRED)

# Try to find ZeroMQ via vcpkg first, fallback to pkg-config
find_package(PkgConfig REQUIRED)
find_package(cppzmq CONFIG QUIET)
if(cppzmq_FOUND)
  message(STATUS "Using vcpkg-managed ZeroMQ")
  set(ZMQ_LIBRARIES cppzmq cppzmq-static)
else()
  message(STATUS "Using system ZeroMQ via pkg-config")
  pkg_check_modules(ZMQ REQUIRED libzmq)
  include_directories(${ZMQ_INCLUDE_DIRS})
  link_directories(${ZMQ_LIBRARY_DIRS})
endif()

# Download and find LibTorch
include(FetchContent)

# Detect PyTorch version from Python installation
find_program(PYTHON_EXECUTABLE python3 python)
execute_process(
  COMMAND ${PYTHON_EXECUTABLE} -c "import torch; print(torch.__version__)"
  OUTPUT_VARIABLE TORCH_VERSION_FROM_PYTHON
  ERROR_QUIET
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

if(TORCH_VERSION_FROM_PYTHON)
  # Extract major.minor.patch from version string (removes any +cpu, +cu118, etc.)
  string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" LIBTORCH_VERSION "${TORCH_VERSION_FROM_PYTHON}")
  message(STATUS "Detected PyTorch version: ${TORCH_VERSION_FROM_PYTHON} -> Using LibTorch: ${LIBTORCH_VERSION}")
else()
  set(LIBTORCH_VERSION "2.7.0")
  message(WARNING "Could not detect PyTorch version, using default: ${LIBTORCH_VERSION}")
endif()

# Determine the correct LibTorch URL based on platform and version
if(APPLE)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    set(LIBTORCH_URL "https://download.pytorch.org/libtorch/cpu/libtorch-macos-arm64-${LIBTORCH_VERSION}.zip")
    set(LIBTORCH_NAME "libtorch-macos-arm64")
  else()
    set(LIBTORCH_URL "https://download.pytorch.org/libtorch/cpu/libtorch-macos-x86_64-${LIBTORCH_VERSION}.zip")
    set(LIBTORCH_NAME "libtorch-macos-x86_64")
  endif()
elseif(WIN32)
  set(LIBTORCH_URL "https://download.pytorch.org/libtorch/cpu/libtorch-win-shared-with-deps-${LIBTORCH_VERSION}%2Bcpu.zip")
  set(LIBTORCH_NAME "libtorch-win")
else()
  # Linux
  set(LIBTORCH_URL "https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-${LIBTORCH_VERSION}%2Bcpu.zip")
  set(LIBTORCH_NAME "libtorch-linux")
endif()

message(STATUS "Downloading LibTorch from: ${LIBTORCH_URL}")

FetchContent_Declare(
  libtorch
  URL ${LIBTORCH_URL}
)

FetchContent_MakeAvailable(libtorch)

# Set the CMAKE_PREFIX_PATH to find LibTorch
list(APPEND CMAKE_PREFIX_PATH ${libtorch_SOURCE_DIR})

# Now find LibTorch
find_package(Torch REQUIRED)

message(STATUS "Found LibTorch ${Torch_VERSION}")
message(STATUS "LibTorch libraries: ${TORCH_LIBRARIES}")
message(STATUS "LibTorch include dirs: ${TORCH_INCLUDE_DIRS}")

# Set C++ standard required by LibTorch
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_program(CCACHE_FOUND ccache)
if(CCACHE_FOUND)
  message(STATUS "CMake using ccache")
  set_property(GLOBAL PROPERTY RULE_LAUNCH_COMPILE ccache)
  set_property(GLOBAL PROPERTY RULE_LAUNCH_LINK ccache)
endif(CCACHE_FOUND)

# macOS codesigning for debugging support
if(APPLE AND EXISTS "${CMAKE_SOURCE_DIR}/debug.entitlements")
  macro(pomagma_add_executable target_name)
    add_executable(${target_name} ${ARGN})
    # Only codesign actual executables (not imported targets)
    get_target_property(target_type ${target_name} TYPE)
    get_target_property(target_imported ${target_name} IMPORTED)
    if(target_type STREQUAL "EXECUTABLE" AND NOT target_imported)
      add_custom_command(TARGET ${target_name} POST_BUILD
        COMMAND codesign -s - -f --entitlements "${CMAKE_SOURCE_DIR}/debug.entitlements" "$<TARGET_FILE:${target_name}>"
        # COMMENT "Code signing ${target_name} for debugging"
        VERBATIM
      )
    endif()
  endmacro()
else()
  macro(pomagma_add_executable)
    add_executable(${ARGV})
  endmacro()
endif()

enable_testing()
set(GTEST_FLAGS "-Wno-error=undef -Wno-undef")

add_subdirectory(src)
