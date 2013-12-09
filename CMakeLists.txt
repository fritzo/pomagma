cmake_minimum_required(VERSION 2.6)
project(pomagma)

#set(LIBRARY_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/lib)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fno-exceptions -fno-rtti")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Woverloaded-virtual -Wsign-promo -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wno-deprecated")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -funswitch-loops -fomit-frame-pointer -pipe")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=native")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp")
# Set -Wno-error=unknown-pragmas when temporarily disabling -fopenmp
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=unknown-pragmas")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DPOMAGMA_ASSUME_X86")

set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS} -DPOMAGMA_DEBUG_LEVEL=9")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "${CMAKE_CXX_FLAGS} -DNDEBUG=1")
#add_definitions(-DPOMAGMA_DEBUG_LEVEL=0)
#add_definitions(-DNDEBUG)

if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
	set(CMAKE_CXX_COMPILER "g++-4.7")
	# see http://stackoverflow.com/questions/10327939
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mno-avx")
	#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wa,-q")
endif(${CMAKE_SYSTEM_NAME} MATCHES "Darwin") 

find_package(Boost 1.48 COMPONENTS thread REQUIRED)
#include_directories(${Boost_INCLUDE_DIR})

# FIXME
#find_package(Protobuf)
#include_directories(${PROTOBUF_INCLUDE_DIRS})
#include_directories(${CMAKE_CURRENT_BINARY_DIR})

enable_testing()

add_subdirectory(src)
