cmake_minimum_required(VERSION 2.6)
project(pomagma)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Woverloaded-virtual -Wsign-promo -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wno-deprecated")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -funswitch-loops -fomit-frame-pointer -pipe")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=native")

if(DEFINED ENV{POMAGMA_NO_OPENMP})
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=unknown-pragmas")
else()
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp")
endif()

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DPOMAGMA_ASSUME_X86")

set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS} -DPOMAGMA_DEBUG_LEVEL=9")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "${CMAKE_CXX_FLAGS} -DNDEBUG=1")

if(APPLE)
	set(CMAKE_CXX_COMPILER "g++-4.7")
	# see http://stackoverflow.com/questions/10327939
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mno-avx")
	#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wa,-q")
endif()

enable_testing()

add_subdirectory(src)
