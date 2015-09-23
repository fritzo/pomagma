cmake_minimum_required(VERSION 2.6)
project(pomagma)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Woverloaded-virtual -Wsign-promo -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wno-deprecated")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -fomit-frame-pointer -pipe")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=native")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DPOMAGMA_ASSUME_X86")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASHSELFTEST=0")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_SSSE3")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_SSE41")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_SSE42")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_ASSUME_AESNI")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DFARMHASH_CAN_USE_CXX11")

set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS} -DPOMAGMA_DEBUG_LEVEL=9")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "${CMAKE_CXX_FLAGS} -DNDEBUG=1")

# Force gcc on apple
#if(APPLE)
#	set(CMAKE_CXX_COMPILER "g++-4.7")
#	# see http://stackoverflow.com/questions/10327939
#	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mno-avx")
#	#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wa,-q")
#endif()

message(STATUS "CMake using ${CMAKE_CXX_COMPILER_ID} C++ compiler")
if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -funswitch-loops")
  if(DEFINED ENV{POMAGMA_NO_OPENMP})
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=unknown-pragmas")
  else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp")
  endif()
elseif("${CMAKE_CXX_COMPILER_ID}" MATCHES "Clang")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=unknown-pragmas") # openmp
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=mismatched-tags")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Qunused-arguments")
  #set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ferror-limit 1")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Intel")
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC")
endif()

find_package(Boost COMPONENTS system filesystem REQUIRED)
include_directories(${Boost_INCLUDE_DIRS})

find_program(CCACHE_FOUND ccache)
if(CCACHE_FOUND)
  message(STATUS "CMake using ccache")
  set_property(GLOBAL PROPERTY RULE_LAUNCH_COMPILE ccache)
  set_property(GLOBAL PROPERTY RULE_LAUNCH_LINK ccache)
endif(CCACHE_FOUND)

enable_testing()

add_subdirectory(src)
