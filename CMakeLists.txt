cmake_minimum_required(VERSION 3.10)
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
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
  
  # Workaround for LLVM 18+ with Abseil compatibility issue
  # See: https://github.com/abseil/abseil-cpp/issues/1747
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fclang-abi-compat=17")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Intel")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC")
endif()
message(STATUS "CMake C++ flags: ${CMAKE_CXX_FLAGS}")

# Handle deprecated FindBoost module warning
if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()

find_package(Boost COMPONENTS system filesystem REQUIRED)
include_directories(${Boost_INCLUDE_DIRS})

# Use modern CMake protobuf and abseil packages
find_package(Protobuf REQUIRED CONFIG)
find_package(absl REQUIRED)

# Find OpenSSL
find_package(OpenSSL REQUIRED)

# Find TBB using pkg-config
find_package(PkgConfig REQUIRED)
pkg_check_modules(TBB REQUIRED tbb)

# Find ZeroMQ using pkg-config
pkg_check_modules(ZMQ REQUIRED libzmq)

# Add TBB include directories as system headers (suppresses warnings)
include_directories(SYSTEM ${TBB_INCLUDE_DIRS})
link_directories(${TBB_LIBRARY_DIRS})

# Add ZeroMQ include directories and library directories
include_directories(${ZMQ_INCLUDE_DIRS})
link_directories(${ZMQ_LIBRARY_DIRS})

find_program(CCACHE_FOUND ccache)
if(CCACHE_FOUND)
  message(STATUS "CMake using ccache")
  set_property(GLOBAL PROPERTY RULE_LAUNCH_COMPILE ccache)
  set_property(GLOBAL PROPERTY RULE_LAUNCH_LINK ccache)
endif(CCACHE_FOUND)

enable_testing()
set(GTEST_FLAGS "-Wno-error=undef -Wno-undef")

add_subdirectory(src)
