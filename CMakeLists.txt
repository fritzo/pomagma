cmake_minimum_required(VERSION 2.6)
project(pomagma)

set(LIBRARY_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/lib)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -fPIC")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")

enable_testing()

#install(TARGETS pomagma LIBRARY DESTINATION ${CMAKE_ROOT}/lib)

add_subdirectory(src)
